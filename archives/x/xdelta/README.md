# xdelta

Binary delta tool and library: generates deltas between pairs of files
(`xdelta delta`) and later applies them (`xdelta patch`), working on binary
files like `diff`/`patch` do on text. Upstream project page:
<https://sourceforge.net/projects/xdelta/> (GPL branch mirror:
<https://github.com/jmacd/xdelta-gpl>).

Successor `xdelta3` (VCDIFF/RFC 3284) is packaged separately as
`archives/x/xdelta3/`.

## Versions

- `1.1.3` — Autotools build, depends on `glib` + `zlib`, ships the `xdelta`
  CLI plus `libxdelta`/`libedsio` libraries.
