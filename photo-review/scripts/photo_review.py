#!/usr/bin/env python3
"""Make a local inventory and contact sheets from JPEG exports.

Adapted from the measurement and contact-sheet routines in the author's
AI-assisted Abba Photo library_filter.py and contact_sheets.py. This public
version records measurements without ranking or rejecting photographs.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


JPEG_EXTENSIONS = {".jpg", ".jpeg"}
WORKING_LONG_EDGE = 1200
GRID_COLUMNS = 10
GRID_ROWS = 7
SHEET_COLUMNS = 4
SHEET_ROWS = 6
THUMB_SIZE = (300, 200)
LABEL_HEIGHT = 44
GAP = 12


def find_jpegs(folder: Path, recursive: bool) -> list[Path]:
    paths = folder.rglob("*") if recursive else folder.iterdir()
    return sorted(
        (path for path in paths if path.is_file() and not path.is_symlink()
         and path.suffix.lower() in JPEG_EXTENSIONS),
        key=lambda path: str(path.relative_to(folder)).casefold(),
    )


def focus_index(gray: np.ndarray) -> float:
    """Return the strongest contrast-normalized tile edge value.

    This retains the local measurement from the private filter, but no
    threshold or photographic quality verdict is attached to it.
    """
    height, width = gray.shape
    y_edges = np.linspace(0, height, GRID_ROWS + 1).astype(int)
    x_edges = np.linspace(0, width, GRID_COLUMNS + 1).astype(int)
    values = []
    for row in range(GRID_ROWS):
        for column in range(GRID_COLUMNS):
            tile = gray[y_edges[row]:y_edges[row + 1], x_edges[column]:x_edges[column + 1]]
            if min(tile.shape) < 3:
                continue
            pixels = tile.astype(np.float32)
            laplacian = (
                -4 * pixels[1:-1, 1:-1]
                + pixels[:-2, 1:-1] + pixels[2:, 1:-1]
                + pixels[1:-1, :-2] + pixels[1:-1, 2:]
            )
            values.append(float(laplacian.var()) / (float(pixels.var()) + 8.0))
    return round(max(values, default=0.0), 4)


def capture_date(image: Image.Image) -> str:
    try:
        exif = image.getexif()
        details = exif.get_ifd(0x8769) if exif else {}
        value = details.get(36867) or details.get(36868) or exif.get(306)
        if isinstance(value, bytes):
            value = value.decode("ascii", errors="replace")
        return str(value).strip() if value else ""
    except (AttributeError, KeyError, TypeError, ValueError):
        return ""


def measure(path: Path, root: Path, number: int) -> dict[str, str | int | float]:
    row: dict[str, str | int | float] = {
        "number": number,
        "filename": str(path.relative_to(root)),
        "bytes": path.stat().st_size,
        "width": "",
        "height": "",
        "capture_date": "",
        "embedded_profile": "",
        "focus_index": "",
        "near_white_pct": "",
        "error": "",
    }
    try:
        with Image.open(path) as original:
            original.load()
            row["capture_date"] = capture_date(original)
            row["embedded_profile"] = "yes" if original.info.get("icc_profile") else "no"
            oriented = ImageOps.exif_transpose(original)
            row["width"], row["height"] = oriented.size
            working = oriented.convert("L")
            working.thumbnail((WORKING_LONG_EDGE, WORKING_LONG_EDGE), Image.Resampling.BILINEAR)
            gray = np.asarray(working, dtype=np.uint8)
            row["focus_index"] = focus_index(gray)
            row["near_white_pct"] = round(float((gray > 247).mean() * 100), 3)
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
    return row


def font() -> ImageFont.ImageFont:
    try:
        return ImageFont.load_default(size=16)
    except TypeError:
        return ImageFont.load_default()


def tile(path: Path, row: dict[str, str | int | float]) -> Image.Image:
    width = THUMB_SIZE[0] + GAP * 2
    height = THUMB_SIZE[1] + LABEL_HEIGHT + GAP * 2
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    try:
        with Image.open(path) as original:
            oriented = ImageOps.exif_transpose(original).convert("RGB")
            oriented.thumbnail(THUMB_SIZE, Image.Resampling.LANCZOS)
            x = GAP + (THUMB_SIZE[0] - oriented.width) // 2
            y = GAP + (THUMB_SIZE[1] - oriented.height) // 2
            canvas.paste(oriented, (x, y))
    except (OSError, ValueError, Image.DecompressionBombError):
        draw.rectangle((GAP, GAP, GAP + THUMB_SIZE[0], GAP + THUMB_SIZE[1]), fill="#f7dddd")
        draw.text((GAP + 12, GAP + 12), "UNREADABLE", fill="#7b0000", font=font())
    filename = str(row["filename"])
    label = filename if len(filename) <= 39 else "..." + filename[-36:]
    draw.text((GAP, GAP + THUMB_SIZE[1] + 3), f"{row['number']}. {label}", fill="black", font=font())
    return canvas


def make_sheets(paths: list[Path], rows: list[dict[str, str | int | float]], folder: Path) -> int:
    folder.mkdir(parents=True)
    per_page = SHEET_COLUMNS * SHEET_ROWS
    tile_width = THUMB_SIZE[0] + GAP * 2
    tile_height = THUMB_SIZE[1] + LABEL_HEIGHT + GAP * 2
    pages = 0
    for start in range(0, len(paths), per_page):
        pages += 1
        count = min(per_page, len(paths) - start)
        page_rows = (count + SHEET_COLUMNS - 1) // SHEET_COLUMNS
        sheet = Image.new("RGB", (tile_width * SHEET_COLUMNS, tile_height * page_rows), "#e9e9e9")
        for offset in range(count):
            index = start + offset
            x = (offset % SHEET_COLUMNS) * tile_width
            y = (offset // SHEET_COLUMNS) * tile_height
            sheet.paste(tile(paths[index], rows[index]), (x, y))
        sheet.save(folder / f"sheet_{pages:03d}.jpg", quality=90, subsampling=0)
    return pages


def run(input_dir: Path, output_dir: Path, recursive: bool) -> tuple[int, int, int]:
    input_dir = input_dir.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    if not input_dir.is_dir():
        raise ValueError(f"Export folder does not exist: {input_dir}")
    if output_dir == input_dir or input_dir in output_dir.parents:
        raise ValueError("Output must be outside the export folder")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"Output folder is not empty: {output_dir}")

    paths = find_jpegs(input_dir, recursive)
    if not paths:
        raise ValueError("No JPEGs found. Export JPEGs or use --recursive for subfolders")
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = [measure(path, input_dir, number) for number, path in enumerate(paths, 1)]
    fields = ["number", "filename", "bytes", "width", "height", "capture_date",
              "embedded_profile", "focus_index", "near_white_pct", "error"]
    with (output_dir / "manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    pages = make_sheets(paths, rows, output_dir / "contact_sheets")
    errors = sum(bool(row["error"]) for row in rows)
    summary = (
        f"Export: {input_dir}\n"
        f"JPEGs: {len(rows)}\nContact sheet pages: {pages}\nRead errors: {errors}\n\n"
        "The CSV and sheets use the same numbers. Original JPEGs were only read.\n"
        "Focus index: strongest contrast-normalized edge tile in a 10 by 7 grid.\n"
        "Near-white percentage: working-size grayscale pixels over 247 of 255.\n"
        "These measurements are review aids, not quality or exposure verdicts.\n"
        "Check photographs at full size before culling or delivering.\n"
    )
    (output_dir / "summary.txt").write_text(summary, encoding="utf-8")
    return len(rows), pages, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("export_folder", type=Path, help="Folder of full-size JPEG exports")
    parser.add_argument("--output", type=Path, help="New empty output folder (default: sibling named <export>-review)")
    parser.add_argument("--recursive", action="store_true", help="Include JPEGs in subfolders")
    args = parser.parse_args()
    export = args.export_folder.expanduser().resolve()
    output = args.output or export.with_name(export.name + "-review")
    try:
        count, pages, errors = run(export, output, args.recursive)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"photo_review: {exc}\n")
    print(f"Wrote {count} rows and {pages} contact sheet page(s) to {output}")
    if errors:
        print(f"{errors} file(s) could not be read; see manifest.csv", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
