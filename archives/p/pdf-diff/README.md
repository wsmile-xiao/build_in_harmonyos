# pdf-diff

## Description

pdf-diff is a Python command-line tool that finds differences between two PDF documents. It compares the text layers of two PDF documents and outputs the bounding boxes of changed text in JSON, and can rasterize the changed pages in the PDFs to a PNG with red outlines around changed text.

## Dependencies

- Python 3.12+
- fast-diff-match-patch
- lxml
- Pillow
- pdftotext (from poppler-utils)

## OHOS Adaptation Notes

- Pure Python package: no C compilation required
- DESTDIR mode uses `setup.py install --prefix=$DEFAULT_PREFIX --root=$TEST_PREFIX` (pip --prefix+--root combination causes "Cannot set --home and --prefix together" error)
- Requires `.pth` file to add `$DEFAULT_PREFIX/lib/python3.12/site-packages` to Python search path
- pip-global Pillow has ELF signing issues; system site-packages Pillow must be used instead

## Version Index

| Version | Status | Date |
|---------|--------|------|
| 0.9.3 | built | 2026-05-28 |