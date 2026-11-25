import tempfile
import unittest
from pathlib import Path
from PIL import Image
from banna.manhattan_graphics import render_manhattan_graphic

KINDS = [
    "mp_fission", "mp_letter", "mp_wartime", "mp_map", "mp_chicago",
    "mp_oakridge", "mp_hanford", "mp_losalamos", "mp_leadership",
    "mp_trinity", "mp_hiroshima", "mp_nagasaki", "mp_legacy",
]

class ManhattanGraphicsTests(unittest.TestCase):
    def test_all_original_stills_render_as_landscape_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            for kind in KINDS:
                output = Path(tmp) / f"{kind}.jpg"
                render_manhattan_graphic(kind, kind.replace("_", " "), output)
                self.assertTrue(output.is_file(), kind)
                with Image.open(output) as image:
                    self.assertEqual(image.size, (1600, 900), kind)

if __name__ == "__main__":
    unittest.main()
