# splint

splint is a tool for statically checking C programs for security
vulnerabilities and coding mistakes, driven by source annotations. It is
built from the upstream autotools release with the OpenHarmony clang
toolchain.

The `3.1.2` recipe has no Conan package requirements: the release tarball
ships its generated parser sources, and `patches/0004` defines `yywrap()`
locally so no `flex`/`libfl` is needed. The recipe packages the `splint`
executable together with its `.lcd` model library under
`share/splint/lib`, and exports `LARCH_PATH` through `runenv_info` so
consumers can run the binary without extra environment setup.

On OHOS `/tmp` is read-only; `patches/0003` makes splint honour the
`TMPDIR` environment variable for its pre-processor scratch files, and
`patches/0001` relaxes the private `umask 077` directory creation that the
HMDFS mount rejects.
