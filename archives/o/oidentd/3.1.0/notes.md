# oidentd 3.1.0 adaptation notes

- Upstream: `https://github.com/janikrabe/oidentd`, tag `v3.1.0` (C, autotools).
- Source: official release asset `oidentd-3.1.0.tar.gz`
  (<https://github.com/janikrabe/oidentd/releases/download/v3.1.0/oidentd-3.1.0.tar.gz>),
  SHA-256 `cb2bdc9da6f136470830e899063be83a6fe9123ac65c5b785b8486e65a6b91b7`.
  The release asset ships the pre-generated `configure`, `config.sub`,
  `install-sh` and the flex/bison outputs (`src/cfg_scan.c`, `src/cfg_parse.c`),
  so no autoreconf/automake/libtool bootstrap is required. The git tag tarball
  (`gh-v3.1.0.tar.gz`) does **not** contain `configure` and must not be used.
- Build system: upstream autotools, in-source only. `configure` appends
  `cp -f $srcdir/src/kernel/$os_src src/os.c` after `config.status`, i.e. the
  platform-specific `os.c` is written inside the source tree, so the recipe sets
  `self.folders.build = "."`.
- Conan dependencies: **none at runtime**. All optional features are disabled
  (`--disable-masq --disable-nat --disable-libnfct`); `masq_support=no` also
  forces `want_libnfct=no`, so libnetfilter_conntrack is never linked.
- Build tooling: `tool_requires("flex/2.6.4")` + `tool_requires("bison/3.8.2")`.
  configure hard-errors when no lexer/parser generator is found
  (`AC_PROG_LEX`/`AC_PROG_YACC` probes), and automake's `BUILT_SOURCES` may
  regenerate `cfg_parse.h/cfg_parse.c/cfg_scan.c` when tarball mtimes are not
  ordered.
- Cross triplets: `AutotoolsToolchain` does not derive OHOS triplets by itself
  (`tools.gnu:host_triplet` is unset in the `ohos-aarch64` profile), so
  `--build=aarch64-linux-ohos --host=aarch64-linux-ohos` are passed explicitly.
  `config.sub` predates HarmonyOS, hence patch 0001.
- Patch 0001 (`patches/0001-config.sub-linux-ohos.patch`) extends only the
  triplet lists in `config.sub`; it introduces **no** `#ifdef __OHOS__`
  platform conditional (R8).
- `package()` relies on Conan's `--sbindir=${prefix}/<first bindir>` mapping
  (`bin` for `package_type = "application"`) to satisfy
  upstream's `sbin_PROGRAMS = oidentd`; no manual `sbin/ → bin/` fold is needed.
  Man pages are installed to `share/man` from the prebuilt files in the
  tarball (the shipped man pages are newer than their `.adoc` sources, so the
  asciidoctor rule never runs).
- Test: `test_package` runs the installed binary with `-v` and asserts the
  `oidentd 3.1.0` banner, the `Build information:` block and
  `Kernel driver: linux`. Upstream ships no automated test suite.
---

**编译结束**: 2026-09-26 22:03
**最终状态**: built
