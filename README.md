# Clothing Photo Classifier

> Public experimental source: see [PUBLICATION.md](PUBLICATION.md) for actual checks, known defects, restored modules and operational limits. Earlier audit decisions are historical.

Python utility that classifies batches of clothing photos with an OpenAI vision model and saves consistently named copies.

## What it does

- accepts a folder from the command line or a native folder picker;
- processes JPG, PNG and WebP images in batches;
- classifies each photo as full-body (`_Main`), partial/angle (`_Angle`) or close-up (`_Detail`);
- detects a shared primary color from the first batch;
- creates deterministic marketplace-oriented filenames;
- preserves originals and writes copies to `renamed_files/`.

## Install

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

Set the API key locally. Never put it in source code:

```powershell
$env:OPENAI_API_KEY = "your-key"
```

## Run

```bash
python main.py "C:\path\to\photos" --barcode 4600000000000
```

Optional arguments:

```bash
python main.py --model gpt-4o --batch-size 10 --barcode 4600000000000
```

Without a folder argument, the application opens a folder picker.

## Version cleanup

The numbered `Classifier.py` through `Classifier5.py` experiments were consolidated into the single `main.py` entry point on 2026-07-06.

## Safety and limitations

The tool sends selected images to the configured OpenAI API. Do not process personal or confidential photos without an appropriate data policy. Model classifications should be reviewed before downstream publication.

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT is recommended for the source code. Model terms and rights to processed images remain separate obligations.
