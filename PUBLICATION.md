# Public source preview — 2026-10-29

OpenAI photo classifier/rename source; all historical Classifier*.py keys are <OPENAI_API_KEY> placeholders and current main uses env. No photos committed.

The complete reachable history was reviewed for credentials, private data and asset provenance. No identified protected-data blocker remains for this source publication. This does not establish that every feature works or that the program is secure to deploy.

## Verification

Current Python source syntax: 1 files checked. Application UI, external APIs, drivers, ML training and real operational data were not exercised for this publication.

Use trusted local input copies and keep personal data, credentials, logs, model weights and generated outputs outside Git. No external scanner, printer password guessing, marketplace automation or model call was executed to publish this source.

## Additional reviewed runtime limits

[
  "Execution uploads selected image contents to OpenAI; no API calls performed.",
  "shutil.copy2(source, destination .jpg) does not convert bytes, so PNG/WebP inputs receive misleading extensions."
]

## Before operational use

"Document remote image transfer and costs. Current output names force .jpg while shutil.copy2 preserves original PNG/WebP bytes; actually convert images or preserve source extension."
