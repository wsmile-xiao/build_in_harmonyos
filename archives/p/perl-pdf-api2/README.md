# perl-pdf-api2

PDF::API2 — A Perl module for creating, modifying, and examining PDF files.

## OHOS Adaptation

- **Pure-Perl module** — no C/XS compilation, no patches needed
- **No E078 issue** — no XS extension modules to trigger musl BIND_NOW
- **Build system**: ExtUtils::MakeMaker (`perl Makefile.PL`)
- **Dependencies**: Font::TTF (optional, for TrueType embedding)
- **Runtime**: requires `PERL5LIB=$DEFAULT_PREFIX/lib/perl5`

## Functional Verification (2026-06-24)

✅ **Fully functional on HarmonyOS** — all 757 official subtests + 54 custom tests pass.

### Tested Capabilities
| Feature | Status |
|---------|--------|
| PDF creation (single/multi-page, 100-page stress) | ✅ |
| Text rendering (fonts, colors, rotation, alignment) | ✅ |
| Graphics (lines, rectangles, circles, polygons) | ✅ |
| Core fonts (Helvetica, Times, Courier, Symbol, ZapfDingbats) | ✅ |
| TrueType font embedding (via Font::TTF) | ✅ |
| Image embedding (PNG/JPEG/GIF/TIFF/PNM) | ✅ |
| PDF I/O (save file/string, open, modify, cycle) | ✅ |
| Metadata (title/author/subject/keywords) | ✅ |
| Annotations (hyperlinks) | ✅ |
| Page properties (mediabox/cropbox/preferences) | ✅ |
