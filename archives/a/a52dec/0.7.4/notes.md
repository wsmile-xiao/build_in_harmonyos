# a52dec 0.7.4 adaptation notes

- Upstream source is the Debian mirror of the original `a52dec-0.7.4` release. The archive is byte-verified by the SHA256 in `conandata.yml`.
- The project uses Autotools and builds the static `liba52` library plus the `a52dec` and `extract_a52` command-line tools.
- The bundled 2002 `config.sub` does not recognize an aarch64 host triple; the single portability patch adds that canonical-machine case.
- `make check` is invoked during `build()`. Its regression data files are not distributed in the release archive, so the upstream scripts report the standard skip status when those streams are unavailable.
- The consumer test links and calls `a52_init()` and `a52_syncinfo()` with valid and invalid AC-3 headers, and verifies the installed `a52dec` executable responds to `--help`.
