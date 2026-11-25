import unittest

from banna.free_photos import _allowed_license, _query_for_scene


class FreePhotoTests(unittest.TestCase):
    def test_accepts_public_domain(self):
        self.assertTrue(_allowed_license({"LicenseShortName": {"value": "Public domain"}})[0])

    def test_accepts_cc_by_sa(self):
        self.assertTrue(_allowed_license({"LicenseShortName": {"value": "CC BY-SA 4.0"}})[0])

    def test_rejects_noncommercial_and_no_derivatives(self):
        self.assertFalse(_allowed_license({"LicenseShortName": {"value": "CC BY-NC 4.0"}})[0])
        self.assertFalse(_allowed_license({"LicenseShortName": {"value": "CC BY-ND 4.0"}})[0])

    def test_prefers_explicit_search_phrase(self):
        self.assertEqual(
            _query_for_scene({"photo_search": "Apollo 11 launch", "title": "Moon"}),
            "Apollo 11 launch",
        )


if __name__ == "__main__":
    unittest.main()
