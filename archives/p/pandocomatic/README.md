# pandocomatic

## Overview

[pandocomatic](https://heerdebeer.org/Software/markdown/pandocomatic/) is a
Ruby application that automates common pandoc document-conversion workflows,
acting as a static-site generator when applied to a directory tree.

**Type**: Ruby application (RubyGem) — not a C/C++ library. It depends on:

- `ruby` (>= 3.1) — runtime interpreter
- `pandoc` — document converter (the engine pandocomatic drives)
- pure-Ruby gems: `paru` (pandoc wrapper), `optimist` (CLI parsing),
  `logger`, plus Ruby stdlib `csv` via paru

## Package layout

- `$PREFIX/gems/` — GEM_HOME with `pandocomatic-2.2.0`, `paru-1.5.2`,
  `optimist-3.2.1`, `logger-1.7.0` installed locally
- `$PREFIX/share/gem/*.gem` — original RubyGems archives for reproducibility

## Usage

Set `GEM_HOME` / `GEM_PATH` (exported by `runenv`) and put Ruby's stdlib gem
dir on `GEM_PATH`, then:

```sh
pandocomatic --version
pandocomatic --help
pandocomatic -i input.md -o output.html
```

## License

GPL-3.0-or-later (pandocomatic/paru), MIT (optimist), Ruby (logger)
