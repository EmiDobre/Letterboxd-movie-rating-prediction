import json
import unittest

from extraction.crawl import parse_film, parse_profile, username
from extraction.prepare import describe, split_rows


class ParsingTests(unittest.TestCase):
    def test_current_markup_half_star_and_unrated(self):
        html = '''<li class="griditem"><div data-item-slug="film-a"><img alt="A"></div>
        <p data-item-uid="film:42"><span class="rating rated-7">★★★½</span></p></li>
        <li class="griditem"><div data-item-slug="film-b"><img alt="B"></div></li>
        <a class="next" href="/alice/films/page/2/">Older</a>'''
        rows, next_url = parse_profile(html, "alice", "source", "time")
        self.assertEqual([r["rating"] for r in rows], [3.5, None])
        self.assertEqual(rows[0]["film_id"], "film:42")
        self.assertEqual(next_url, "https://letterboxd.com/alice/films/page/2/")

    def test_old_markup_and_last_page(self):
        html = '<li class="poster-container"><div data-film-slug="a"></div><span class="rating rated-1"></span></li>'
        rows, next_url = parse_profile(html, "alice", "source", "time")
        self.assertEqual(rows[0]["rating"], 0.5)
        self.assertIsNone(next_url)

    def test_blocked_page_fails(self):
        with self.assertRaises(ValueError):
            parse_profile("<h1>Verify you are human</h1>", "alice", "source", "time")

    def test_movie_jsonld(self):
        movie = {"@type": "Movie", "name": "Film", "dateCreated": "2010-07-08",
                 "duration": "PT2H28M", "genre": ["Action"], "director": {"name": "Director"},
                 "countryOfOrigin": [{"name": "UK"}], "inLanguage": ["en"],
                 "aggregateRating": {"ratingValue": 4.2, "ratingCount": 123}}
        html = '<script type="application/ld+json">/* <![CDATA[ */' + json.dumps(movie) + '/* ]]> */</script>'
        row = parse_film(html, "film", "source", "time")
        self.assertEqual(row["runtime_minutes"], 148)
        self.assertEqual(row["directors"], ["Director"])
        self.assertEqual(row["release_year"], 2010)
        self.assertEqual(row["cast"], [])

    def test_user_validation(self):
        self.assertEqual(username("https://letterboxd.com/Alice/"), "alice")
        for value in ["../secret", "https://example.com/alice", "https://letterboxd.com/a/films/"]:
            with self.assertRaises(ValueError):
                username(value)


class SplitTests(unittest.TestCase):
    def test_fixed_sizes_and_insufficient_user(self):
        rows = [{"user_id": user, "film_slug": f"f-{i}", "rating": 4.0}
                for user, count in [("a", 479), ("b", 400), ("c", 399)] for i in range(count)]
        train, test = split_rows(rows, train_size=300, test_size=100)
        self.assertEqual((len(train), len(test)), (600, 200))
        self.assertEqual((train, test), split_rows(list(reversed(rows)), train_size=300, test_size=100))
        self.assertEqual({r["user_id"] for r in train + test}, {"a", "b"})
        self.assertFalse({(r["user_id"], r["film_slug"]) for r in train} &
                         {(r["user_id"], r["film_slug"]) for r in test})

    def setUp(self):
        self.rows = [{"user_id": user, "film_slug": f"film-{i}", "rating": (i % 10 + 1) / 2}
                     for user in ["alice", "bob"] for i in range(20)]

    def test_disjoint_reproducible_per_user(self):
        train, test = split_rows(self.rows)
        self.assertEqual((len(train), len(test)), (32, 8))
        self.assertEqual((train, test), split_rows(list(reversed(self.rows))))
        pairs = lambda rows: {(r["user_id"], r["film_slug"]) for r in rows}
        self.assertFalse(pairs(train) & pairs(test))
        self.assertEqual(pairs(train) | pairs(test), pairs(self.rows))
        for user in ["alice", "bob"]:
            self.assertEqual(sum(r["user_id"] == user for r in test), 4)

    def test_singleton_and_unrated(self):
        rows = [{"user_id": "a", "film_slug": "one", "rating": 2.5},
                {"user_id": "b", "film_slug": "two", "rating": None}]
        train, test = split_rows(rows)
        self.assertEqual(train, rows[:1])
        self.assertEqual(test, [])

    def test_duplicates_and_invalid_ratings_fail(self):
        with self.assertRaises(ValueError):
            split_rows(self.rows + self.rows[:1])
        for rating in [0, 6, 2.3, float("nan"), True]:
            with self.assertRaises(ValueError):
                split_rows([{"user_id": "a", "film_slug": "b", "rating": rating}])

    def test_report(self):
        train, test = split_rows(self.rows)
        report = describe(self.rows, [{"film_slug": f"film-{i}"} for i in range(20)], train, test)
        self.assertEqual(report["rated_interactions"], 40)
        self.assertEqual(report["films_rated_by_multiple_users"], 20)
        self.assertEqual(report["missing_metadata"]["release_year"], 20)


if __name__ == "__main__":
    unittest.main()
