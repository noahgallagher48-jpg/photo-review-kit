import csv
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SCRIPT = Path(__file__).resolve().parents[1] / "photo-review" / "scripts" / "photo_review.py"
SPEC = importlib.util.spec_from_file_location("photo_review", SCRIPT)
photo_review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(photo_review)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PhotoReviewTests(unittest.TestCase):
    def test_inventory_pages_errors_and_unchanged_originals(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            exports = root / "exports"
            exports.mkdir()
            for number in range(25):
                image = Image.new("RGB", (120 + number, 90), (number * 7 % 255, 60, 120))
                image.save(exports / f"frame_{number:02d}.jpg")
            (exports / "frame_25.jpg").write_bytes(b"not a JPEG")
            before = {p.name: digest(p) for p in exports.iterdir()}

            output = root / "review"
            count, pages, errors = photo_review.run(exports, output, False)

            self.assertEqual((count, pages, errors), (26, 2, 1))
            self.assertEqual(before, {p.name: digest(p) for p in exports.iterdir()})
            with (output / "manifest.csv").open(newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([row["number"] for row in rows], [str(i) for i in range(1, 27)])
            self.assertEqual(rows[0]["filename"], "frame_00.jpg")
            self.assertEqual(rows[0]["width"], "120")
            self.assertTrue(rows[0]["focus_index"])
            self.assertIn("UnidentifiedImageError", rows[-1]["error"])
            self.assertTrue((output / "contact_sheets" / "sheet_001.jpg").is_file())
            self.assertTrue((output / "contact_sheets" / "sheet_002.jpg").is_file())
            self.assertIn("Read errors: 1", (output / "summary.txt").read_text())

    def test_recursive_selection_and_output_guards(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            exports = root / "exports"
            nested = exports / "subfolder"
            nested.mkdir(parents=True)
            Image.new("RGB", (80, 60), "blue").save(nested / "one.jpeg")
            with self.assertRaisesRegex(ValueError, "No JPEGs found"):
                photo_review.run(exports, root / "flat-review", False)
            count, _, _ = photo_review.run(exports, root / "nested-review", True)
            self.assertEqual(count, 1)
            with self.assertRaisesRegex(ValueError, "outside the export"):
                photo_review.run(exports, exports / "review", True)
            with self.assertRaisesRegex(ValueError, "not empty"):
                photo_review.run(exports, root / "nested-review", True)

    def test_orientation_and_capture_date_are_read_from_export(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            exports = root / "exports"
            exports.mkdir()
            image = Image.new("RGB", (120, 80), "orange")
            exif = Image.Exif()
            exif[274] = 6
            exif[306] = "2026:09:29 10:00:00"
            image.save(exports / "oriented.jpg", exif=exif)
            photo_review.run(exports, root / "review", False)
            with (root / "review" / "manifest.csv").open(newline="") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual((row["width"], row["height"]), ("80", "120"))
            self.assertEqual(row["capture_date"], "2026:09:29 10:00:00")


if __name__ == "__main__":
    unittest.main()
