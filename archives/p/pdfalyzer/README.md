# pdfalyzer

PDF analysis tool that combines yara rules, binary analysis, and PDF structure parsing.

## What it does

pdfalyzer analyzes PDF files using:
- **YARA rules** for pattern detection in embedded streams
- **anytree** for PDF object hierarchy visualization
- **pypdf** for PDF parsing and extraction

## OpenHarmony Adaptation

- Built as a Python package using `pip install --target`
- Core dependency `yara-python` requires C compilation (libyara built from source)
- All dependencies are bundled in the precompiled package

## Dependencies

- yara-python >=4.5.4 (C extension with native .so)
- yaralyzer ==1.3.17
- anytree ~=2.13
- pypdf ==6.6.0
- rich ==14.2.0

## Installation

After extracting the precompiled tar.gz:

```bash
# Set PYTHONPATH to include the installed site-packages
export PYTHONPATH=$HOME/usr/local/lib/python3.12/site-packages
pdfalyze --help
```