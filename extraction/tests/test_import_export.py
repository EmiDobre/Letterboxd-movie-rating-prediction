import unittest

from extraction.import_export import import_rows


class ImportTests(unittest.TestCase):
    def test_rating_overrides_watched_and_alias(self):
        film = {"Name": "Example", "Letterboxd URI": "https://letterboxd.com/film/example/"}
        other = {"Name": "Other", "Letterboxd URI": "https://letterboxd.com/film/other/"}
        rows = import_rows("taciinplm", [dict(film, Rating="3.5")], [film, other])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["user_id"], "daria")
        self.assertEqual(rows[0]["rating"], 3.5)
        self.assertIsNone(rows[1]["rating"])

    def test_invalid_rating_and_url(self):
        film = {"Name": "Example", "Letterboxd URI": "https://letterboxd.com/film/example/", "Rating": "7"}
        with self.assertRaises(ValueError):
            import_rows("alice", [film], [])
        with self.assertRaises(ValueError):
            import_rows("alice", [dict(film, **{"Letterboxd URI": "https://example.org/film/example/"})], [])


if __name__ == "__main__":
    unittest.main()
