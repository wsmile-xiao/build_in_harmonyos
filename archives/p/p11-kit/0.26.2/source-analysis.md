# Source and build analysis: p11-kit 0.26.2

## Source integrity

- Release archive: `p11-kit-0.26.2.tar.xz`
- SHA-256: `09fd9f44da4813a3141e73d5e7cf7008e5660d0405f13d56c15e1da9dcecf828`
- Upstream version: 0.26.2
- Build systems: Meson and Autotools; this recipe uses Meson.

The release includes the RPC null-dereference fix identified upstream as
CVE-2026-2100. Upstream did not add a dedicated regression test in the release
commit, so the focused test set retains both RPC suites.

## Selected feature set

The build keeps the main shared library, public headers, pkg-config metadata,
the PKCS#11 client/proxy modules, and the public `p11-kit` command. It disables
the trust module, systemd integration, translations, documentation, and shell
completion. This removes all mandatory third-party dependencies.

Meson emits `libp11-kit.so.0.4.8` with SONAME `libp11-kit.so.0`. The recipe
preserves Meson's links when supported and copies the real ELF to any missing
loader/linker aliases when the device workspace rejects link creation.

## Package ownership boundary

Upstream always installs private `p11-kit-server` and `p11-kit-remote` commands
from this source tree. They are removed from this core package because issue
2072 owns them through the separate `p11-kit-server/0.26.2` recipe. Keeping the
boundary avoids overlapping files and duplicate Conan ownership.

## HarmonyOS checkpoints

- Meson archiver paths are injected from the Conan profile into both native and
  cross files when Conan omits them.
- Temporary files are redirected into the Conan build directory on OHOS.
- Upstream environment path overrides are enabled, and Conan run metadata points
  module/config lookups at the relocated package directory instead of the build
  cache prefix compiled by Meson.
- Meson may rewrite ELF metadata during install, so packaged ELF files are
  re-signed when the device signing tools are available.
- Shadow CI confirmed `SO_PEERCRED` support in `unix-peer.c`, SONAME
  `libp11-kit.so.0`, consumer linking/loading, and all four focused upstream
  tests on HarmonyOS aarch64.
