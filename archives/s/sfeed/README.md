# sfeed

sfeed is an RSS and Atom parser with small format conversion tools. It converts
feeds from XML to a tab-separated format and provides formatter commands such as
`sfeed_plain`, `sfeed_html`, `sfeed_json`, `sfeed_mbox`, and `sfeed_twtxt`.

## OpenHarmony PC Adaptation

- Builds with the upstream POSIX Makefile.
- Disables the optional curses UI with `SFEED_CURSES=""`.
- Packages parser and formatter commands under `bin`.
- Adds a deterministic Conan consumer test using local Atom and OPML fixtures.

## Validation

- Source SHA256 verified.
- Upstream release has no formal test suite.
- Consumer test validates 12 command/output assertions.
