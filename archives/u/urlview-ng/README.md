# urlview-ng

URL extractor and launcher for terminal applications.

## Description

urlview-ng is a modern rewrite of the classic urlview utility. It extracts URLs from text files or piped input and provides an interactive menu to select and launch URLs using a configurable handler.

## Features

- Extract URLs from text files, email, or any text input
- Interactive terminal-based URL selection menu
- Configurable URL handler (default: url_handler.sh)
- Support for various URL schemes: http, https, ftp, gopher, gemini, mailto
- Wide character support (ncursesw)
- Internationalization (i18n) support

## Versions

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 1e | built | 2026-06-03 | Makefile project, requires ncursesw |

## Dependencies

- ncursesw (wide character support)
- libintl (gettext for i18n)

## Usage

```bash
# Extract URLs from a file
urlview README

# Extract URLs from piped input
cat email.txt | urlview

# Use custom handler
urlview -c /path/to/handler file.txt
```

## Configuration

Default configuration file: `/etc/urlview.conf`
Sample configuration: `sample.urlview`

## Build Notes

urlview-ng uses a pure Makefile build system (no configure script).

Known adaptations for OpenHarmony:
- ncursesw6-config prefix path fix required
- reallocarray → realloc (musl limitation)
- NCURSES_BOOL conflict resolution
- Wide character function declarations

## Links

- Source: https://git.sr.ht/~nabijaczleweli/urlview-ng
- Original: https://packages.debian.org/sid/source/urlview