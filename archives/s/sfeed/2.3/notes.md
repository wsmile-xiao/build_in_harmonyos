# sfeed 2.3

## Source

- URL: https://codemadness.org/releases/sfeed/sfeed-2.3.tar.gz
- SHA256: `a1daa0ecbe0b77e7540de8d9781d9645e0c068135e1767a54fdc6c380c0c48b7`
- License: ISC

## Build

sfeed uses a POSIX Makefile. The default build includes `sfeed_curses`, which
requires a curses implementation. The recipe builds the core parser and format
tools with:

```sh
make -j1 SFEED_CURSES=""
```

This keeps the package focused on the RSS/Atom parser and deterministic format
conversion tools.

## Upstream Tests

The 2.3 release archive does not provide a formal `tests/`, `make check`,
CTest, or equivalent upstream test suite. The upstream README documents manual
usage examples, but those are not registered test cases.

## Consumer Test

The Conan `test_package` creates local Atom and OPML fixtures, then executes
the packaged commands:

- `sfeed`
- `sfeed_plain`
- `sfeed_html`
- `sfeed_json`
- `sfeed_mbox`
- `sfeed_twtxt`
- `sfeed_opml_import`
- `sfeed_opml_export`
- `sfeed_xmlenc`

The test performs 12 deterministic assertions against parsed titles, links,
authors, feed formatting output, OPML conversion, and XML encoding detection.
