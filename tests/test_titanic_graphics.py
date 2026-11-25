import tempfile
import unittest
from pathlib import Path
from PIL import Image

from banna.titanic_graphics import render_titanic_graphic


class TitanicGraphicTests(unittest.TestCase):
    def test_all_original_titanic_reconstructions_render_1080p_assets(self):
        with tempfile.TemporaryDirectory() as folder:
            for kind in ("atlantic_route_map", "iceberg_collision", "ship_cross_section", "sinking_ship"):
                target = Path(folder) / f"{kind}.jpg"
                render_titanic_graphic(kind, "Titanic evidence", target)
                self.assertTrue(target.is_file())
                with Image.open(target) as image:
                    self.assertEqual(image.size, (1600, 900))


if __name__ == "__main__":
    unittest.main()
