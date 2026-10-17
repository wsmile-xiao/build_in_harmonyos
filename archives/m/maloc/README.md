# maloc

Minimal Abstraction Layer for Object-oriented C (libmaloc) adapted for OpenHarmony PC.

- Upstream: http://www.fetk.org/codes/ (downloads: http://www.fetk.org/codes/download/)
- Version: 1.5
- Current package: `archives/m/maloc/1.5`
- Supported OpenHarmony architecture: armv8
- Artifacts actually packaged: `lib/libmaloc.a` (static only, `--disable-shared`)
  and headers under `include/maloc/`. Upstream `tools/Makefile.am:40` declares
  `bin_PROGRAMS = malocbridge`, but that tree is not part of this build, so no
  `bin/` artifact is produced and `cpp_info.bindirs` is declared empty.
- Source retrieval note: upstream serves the tarball over plaintext http only;
  `https://fetk.org/...` and `https://www.fetk.org/...` do not complete the TLS
  handshake (certificate CN does not cover www.fetk.org). See `1.5/notes.md`.
