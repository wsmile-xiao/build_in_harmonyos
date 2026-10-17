# lesspipe 2.27 adaptation notes

## Scope

- Package: lesspipe
- Conan version path: 2.27
- Upstream release: v2.27 (https://github.com/wofr06/lesspipe, tag v2.27)
- Task: #13491

## What lesspipe is

lesspipe is a pure shell (bash) input filter for the less pager. It lets
less display 100+ file formats (archives, compressed files, documents)
by piping them through suitable converters. The deliverables are shell
scripts (`lesspipe.sh`, `archive_color`, `lesscomplete`, completion files)
and a man page — there is no C/C++ code and nothing to compile.

## Build system notes

- `./configure` only checks for a usable bash (>= 5.0) and generates a
  Makefile with install rules; it also rewrites shebangs. No compilation
  takes place.
- OHOS ships GNU bash 5.3, so the upstream `#!/usr/bin/env bash` shebang
  works unmodified.
- The recipe therefore skips configure (it would only generate a Makefile
  that is not needed) and packages the scripts directly, following the
  established script-package precedent in this repository (latexdiff 1.4.0).

## Platform adaptation (the real work)

lesspipe detects file types through `file -L -s -b --mime`. The OHOS
system `file` is toybox 0.8.12 which has **no --mime option** (only
`-bhLs`). Without adaptation `filetype()` returns an empty type and every
mime-dependent path (gzip, bzip2, xz, zstd, lzma, tar, zip, jar, deb, ar,
rar, 7z, ...) degrades to raw binary passthrough.

Patch `0001-ohos-toybox-file-mime-fallback.patch` adds a fallback inside
`filetype()`: when `file --mime` returns nothing, the plain toybox
`file -L -s -b` description is mapped to the equivalent mime type
(tar/zip/gzip/bzip2/xz/zstd/ar/7z/text/directory), with two extra magic
probes that toybox cannot express:

- Debian packages are `ar archive` + `debian-binary` marker (first 32
  bytes) -> application/vnd.debian.binary-package
- RAR archives are reported as plain `data` by toybox -> Rar! magic
  (first 4 bytes) -> application/x-rar

Text detection sets charset=utf-8 so plain files keep the `cat` path
instead of being routed through `strings`.

## Upstream tests (real run, no skipping)

`./test.sh` registers 134 numbered tests. Tests that require optional
external tools (rpm2cpio, pandoc, vimcolor, pygmentize, GNU cpio, ...)
are auto-ignored by the suite itself when the tool is missing.

- Before patch: 41 passed / 73 ignored / 20 FAILED
- After patch:  61 passed / 73 ignored / 0 failed  (77 s)

The 20 fixed failures were all caused by the missing mime detection:
tar member extraction (4, 5, 7), chained archives (20, 21), deb (24,
25), rar (28, 29), ar (46, 47), bzip2 (50), lzma (52), xz (53), lz4
(56), binary data via strings (90), special-character archive members
(114, 116, 118, 119).

The remaining 73 ignored tests need tools that are neither part of
lesspipe nor of the base OHOS system (they are optional integrations);
the suite prints `needs <tool>` for each one.

## Packaging layout

- bin/lesspipe.sh, bin/archive_color (0755)
- libexec/lesspipe/lesscomplete (0755)
- share/man/man1/lesspipe.1
- share/bash-completion/completions/less, share/zsh/site-functions/_less
  (with __LIBEXECDIR__ substituted to libexec/lesspipe)
- licenses/LICENSE

## test_package

test_lesspipe.py verifies: deliverable files exist and are executable,
the no-argument setup hint prints the LESSOPEN line referencing the
installed path, the packaged script is version 2.27 and contains the
OHOS toybox fallback, and two real end-to-end previews work on the
OHOS host: a gzip file is decompressed through the fallback detection
and a tar.gz archive is listed.

## Validation environment

- Local OHOS PC (aarch64, bash 5.3, toybox 0.8.12, perl 5.42) — the same
  tool family available on CI workers.
- Upstream suite: 61/61 executed tests passed, 0 failed, 73 auto-ignored
  (missing optional tools), total registered 134.
- conan create with the ohos-aarch64 profile: see PR CI (authoritative).
