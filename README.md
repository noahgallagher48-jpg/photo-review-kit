# Photo Review Kit

A local tool for photographers with a folder of full-size JPEG exports. It writes a CSV inventory and numbered contact sheets. It does not move, rename, edit, delete, upload, or rate the originals.

The Python script is the **code**. [`photo-review/SKILL.md`](photo-review/SKILL.md) is an optional **skill**: instructions for an AI assistant to run that same script, explain the report, and keep the photographer in charge of the edit. The script works without an AI assistant or an account.

The code and skill are offered under the [MIT License](LICENSE).

This public version is adapted from the local measurement and contact-sheet code I built with AI for my own photography workflow. It deliberately omits client-specific labels, calibrated thresholds, cloud calls, and delivery-site code. It is a review aid, not an automatic culling system.

## Run the code

Requires Python 3.10 or newer.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r photo-review/requirements.txt
.venv/bin/python photo-review/scripts/photo_review.py /path/to/full-size-jpegs
```

The default output is a new sibling folder named `<export-folder>-review`. To choose another location:

```bash
.venv/bin/python photo-review/scripts/photo_review.py /path/to/full-size-jpegs --output /path/to/review-output --recursive
```

The output folder must not already contain files and must be outside the export folder. The script reads `.jpg` and `.jpeg` files only. It creates:

- `manifest.csv`: one row per JPEG, with its relative filename, dimensions, file size, capture date when available, profile presence, a focus index, a near-white percentage, and any read error.
- `contact_sheets/sheet_001.jpg` and following pages: every readable frame, fit inside its tile without cropping, numbered to match the manifest.
- `summary.txt`: counts and an explanation of the measurements.

The focus index is a local edge measurement adapted from my original filter. It is not a verdict on focus, artistic quality, or which frames to deliver. Near-white pixels are not proof of blown highlights. Open the photographs at full size before deciding. No files are sent to an AI model or any network service by the script.

## Use the skill

Copy the `photo-review` folder to a skills directory supported by your AI assistant. For Codex, that is usually `~/.codex/skills/photo-review`. Ask the assistant to use `photo-review` with the path to your exported JPEGs. The skill uses the included script. It does not change the script's read-only treatment of the originals.

## Scope and provenance

The measurements and contact-sheet layout are a shareable extraction of `library_filter.py` and `contact_sheets.py` from my private Abba Photo workflow, written with AI assistance. The public version has a smaller interface and no private paths, names, training examples, model prompts, or cloud integration. It makes no claim that its technical measurements match a photographer's taste.
