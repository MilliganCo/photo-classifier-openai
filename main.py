from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

from openai import OpenAI

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIEW_TYPES = {"_Main", "_Angle", "_Detail"}


def choose_folder() -> Path | None:
    root = tk.Tk()
    root.withdraw()
    selected = filedialog.askdirectory()
    root.destroy()
    return Path(selected) if selected else None


def image_part(path: Path) -> dict:
    mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
    }


def parse_json(content: str) -> object:
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
    return json.loads(fenced.group(1) if fenced else content)


def classify_batch(
    client: OpenAI,
    image_paths: list[Path],
    model: str,
    detect_color: bool,
) -> tuple[str | None, list[str]]:
    color_instruction = (
        'Return an object with "color" for the primary color of the first image and '
        '"classifications" as the ordered array.'
        if detect_color
        else "Return only the ordered JSON array."
    )
    prompt = f"""
Classify every clothing image as exactly one of:
- _Main: the full model is visible from head to feet;
- _Angle: medium or partial-body framing;
- _Detail: a close-up of garment details or material.

Each array item must have this shape: {{"view_type": "_Main"}}.
{color_instruction}
Do not include commentary outside JSON.
""".strip()

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}]
                + [image_part(path) for path in image_paths],
            }
        ],
        max_tokens=500,
        temperature=0,
    )
    parsed = parse_json(response.choices[0].message.content or "")

    if detect_color:
        if not isinstance(parsed, dict):
            raise ValueError("Expected an object containing color and classifications")
        color = str(parsed.get("color") or "unknown")
        items = parsed.get("classifications")
    else:
        color = None
        items = parsed

    if not isinstance(items, list) or len(items) != len(image_paths):
        raise ValueError("The model returned a different number of classifications")

    classifications: list[str] = []
    for item in items:
        view_type = item.get("view_type") if isinstance(item, dict) else None
        classifications.append(view_type if view_type in VIEW_TYPES else "_NotClassified")
    return color, classifications


def safe_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip())
    return cleaned.strip("-") or "unknown"


def output_name(barcode: str, view_type: str, color: str, index: int) -> str:
    return f"{safe_component(barcode)}{view_type}_Model_1_{safe_component(color)}_{index}.jpg"


def run(folder: Path, model: str, batch_size: int, barcode: str) -> Path:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY before running the classifier")

    files = sorted(
        path for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not files:
        raise RuntimeError(f"No supported images found in {folder}")

    output_dir = folder / "renamed_files"
    output_dir.mkdir(exist_ok=True)
    client = OpenAI()
    detected_color: str | None = None

    for start in range(0, len(files), batch_size):
        batch = files[start : start + batch_size]
        color, view_types = classify_batch(
            client,
            batch,
            model=model,
            detect_color=detected_color is None,
        )
        if color:
            detected_color = color

        for index, (source, view_type) in enumerate(
            zip(batch, view_types), start=start + 1
        ):
            destination = output_dir / output_name(
                barcode, view_type, detected_color or "unknown", index
            )
            shutil.copy2(source, destination)
            print(f"{source.name} -> {destination.name}")

    return output_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Classify and consistently rename clothing photos with OpenAI vision."
    )
    parser.add_argument("folder", nargs="?", type=Path)
    parser.add_argument("--model", default="gpt-4o")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--barcode", default="0000000000000")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not 1 <= args.batch_size <= 20:
        raise SystemExit("--batch-size must be between 1 and 20")

    folder = args.folder or choose_folder()
    if folder is None:
        raise SystemExit("No folder selected")
    if not folder.is_dir():
        raise SystemExit(f"Folder does not exist: {folder}")

    output_dir = run(folder, args.model, args.batch_size, args.barcode)
    print(f"Done. Renamed copies are in: {output_dir}")


if __name__ == "__main__":
    main()
