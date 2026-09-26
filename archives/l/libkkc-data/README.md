# libkkc-data

https://github.com/ueno/libkkc

This project provides the language model data used by
[libkkc](https://github.com/ueno/libkkc), a Japanese Kana-Kanji conversion
engine. It ships a large 3-gram arpa corpus
(`data/models/text3/data.arpa`, ~137 MB) together with two Python tools
(`tools/sortlm.py`, `tools/genfilter.py`) that convert the corpus into the
binary trie- and cost tables (`data/models/sorted3/`) consumed by libkkc at
runtime.

## Installation

The Conan package is data-only and installs the generated model files to:

- `lib/libkkc/models/sorted3/` — 7 binary model files + `metadata.json`

The model is generated at build time from the official corpus using the exact
upstream commands from `data/models/Makefile.am`. Generation is
deterministic, so the packaged files are byte-identical across builds (the
test_package pins their SHA256 references).

build-time inputs (no Conan dependency):

- the upstream marisa-trie 0.3.1 sources, pinned by sha256 in `conandata.yml`
  (`marisa_sources`) and extracted to `build-tools/marisa-trie/`
- `bindings/marisa_tool.cc`, compiled into the `marisa_tool` helper, which
  builds and saves the `*.1gram.index` / `*.input` tries and reports every
  key id. The marisa trie is never shipped in the package.

The helper is compiled for the machine that runs the tools, in the same single
command as marisa itself, so the helper and the trie share one ABI everywhere.
That is also why this is not a `tool_requires marisa/0.3.1`: a Conan package
resolves for the profile's context, so a build machine whose profile differs
from `ohos-aarch64` would either find no binary or get a library produced by a
different compiler (on the default Windows profile that is an MSVC
`marisa.lib`, which MinGW g++/clang++ cannot link).

The compiler is looked up in order (explicit `CXX`, `PATH`, the profile's
`tools.build:compiler_executables`, then the usual install locations) and every
candidate is verified by compiling *and* running its `selftest`; the CI worker
keeps its toolchain outside the recipe interpreter's `PATH`, so a plain
`shutil.which` lookup is not enough there. The first combination that produces
a helper this machine can start is used, and `-static-libstdc++` is preferred
so the helper does not depend on the SDK library directory being on the loader
path.

The helper runs out of process on purpose: on the OHOS build worker the
sandbox only lets a process load shared objects that carry the `hnp_file`
security label, while build products live in user-owned paths (hmdfs label),
so a CPython extension module built from the same sources cannot be imported
there (`ImportError: Error loading shared library ... Permission denied`;
hmmac security labels, see knowledge entry E212).
