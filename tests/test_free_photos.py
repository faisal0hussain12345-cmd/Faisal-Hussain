import unittest

from banna.free_photos import _allowed_license, _query_for_scene, _is_titanic_scene, STATIC_TITANIC_ARCHIVE


class FreePhotoTests(unittest.TestCase):
    def test_accepts_public_domain(self):
        self.assertTrue(_allowed_license({"LicenseShortName": {"value": "Public domain"}})[0])

    def test_accepts_cc_by_sa(self):
        self.assertTrue(_allowed_license({"LicenseShortName": {"value": "CC BY-SA 4.0"}})[0])

    def test_rejects_noncommercial_and_no_derivatives(self):
        self.assertFalse(_allowed_license({"LicenseShortName": {"value": "CC BY-NC 4.0"}})[0])
        self.assertFalse(_allowed_license({"LicenseShortName": {"value": "CC BY-ND 4.0"}})[0])

    def test_curated_titanic_scenes_have_verified_archive_sources(self):
        for scene_id in ("opening", "shipyard", "luxury", "lifeboats", "rescue", "aftermath", "wreck"):
            self.assertIn(scene_id, STATIC_TITANIC_ARCHIVE)
            image_url, source_page, title, rights = STATIC_TITANIC_ARCHIVE[scene_id]
            self.assertTrue(image_url.startswith("https://"))
            self.assertTrue(source_page.startswith("https://"))
            self.assertTrue(title)
            self.assertTrue(rights)

    def test_titanic_curated_images_do_not_leak_into_manhattan_project(self):
        self.assertFalse(_is_titanic_scene({
            "id": "opening",
            "project_name": "The Manhattan Project",
            "photo_search": "Manhattan Project workers Oak Ridge 1944",
        }))
        self.assertTrue(_is_titanic_scene({
            "id": "opening",
            "project_name": "Titanic documentary",
        }))

    def test_prefers_explicit_search_phrase(self):
        self.assertEqual(
            _query_for_scene({"photo_search": "Apollo 11 launch", "title": "Moon"}),
            "Apollo 11 launch",
        )


if __name__ == "__main__":
    unittest.main()
