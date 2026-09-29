---
name: photo-review
description: Build a local CSV inventory and numbered contact sheets from a photographer's exported JPEG folder. Use when a photographer wants a review aid for an export; do not use it to decide artistic quality or deliver client files.
---

# Photo review

Use `scripts/photo_review.py` to prepare a review kit from full-size JPEG exports. The script runs locally, reads originals, and writes only to a new output folder. It does not upload images or select winners.

1. Get the path to the export folder. Use `--recursive` only when the photographer wants subfolders included. Locate `scripts/photo_review.py` relative to this `SKILL.md` file, regardless of the current working directory, and run it with `--help` if you need the options.
2. If Pillow or NumPy are missing, install `requirements.txt` in a virtual environment. Do not alter the photographer's files or use a cloud vision service as part of this workflow.
3. Run the script with the export path and, if needed, `--output` for a new empty folder outside the export. Report the paths to `manifest.csv`, `summary.txt`, and the contact sheets.
4. Read `summary.txt` and the manifest before describing the result. Explain that the focus index and near-white percentage are measurements, not quality judgments. A read error means that file needs a manual check.
5. Leave culling and folder assignments to the photographer. If asked to organize selections, first obtain their selection list and intended folder names; make copies only when they explicitly request that action.

The code is the executable tool. This skill is the assistant's operating guide for it. Someone can run the code directly without installing the skill.
