# discount 2.2.7 Release Notes

## Release Information

- **Version**: 2.2.7
- **Release Date**: 2026-04-30
- **Platform**: HarmonyOS (aarch64)

## What's New

This is the first HarmonyOS release of discount, a fast C implementation
of Markdown markup language.

## Key Changes

### Platform Adaptations

1. **HMDFS Hard Link Fix**: Replaced hard links with file copies in librarian.sh
2. **Install Command**: Created POSIX-compliant install.sh replacement for missing BSD install command

## Known Issues

- Old-style function definition warnings (不影响功能)

## Included Programs

- `markdown` - Markdown parser
- `mkd2html` - Convert markdown to HTML
- `makepage` - Generate page with default CSS
- `theme` - Theme generator

## Included Libraries

- `libmarkdown.a` - Static library for markdown processing
- `libmarkdown.pc` - pkg-config file

## Installation

Run `install.sh` to deploy to ~/usr/local:

```bash
tar xzf discount-2.2.7-ohos-aarch64.tar.gz
cd discount-2.2.7
./install.sh
```

## License

BSD-style license