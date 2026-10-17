# libxrender 0.9.12 adaptation notes

## Evidence status

- Source version: 0.9.12, the highest stable release listed by X.Org on
  2026-08-10.
- Source SHA256: `b832128da48b39c8d608224481743403ad1691bf4e554e4be9c174df171d1b97`.
- Current main base: `f06dafbfc326bbbaf1bfcd423abe72b43dcf1654`.
- Candidate HEAD: `7c9b04980cce274df7f432baa6a0b43cd2e82bc7`.
- Fresh isolated OHOS/arm64 W0 r12: graph and install both passed with
  `--build=never` for shared and static modes; all eight dependency nodes have
  RREV/PID/PREV, `binary_remote=ohpcd`, and empty `info_invalid`.
- Generated configure arguments are mutually exclusive and unique: shared has
  one `--enable-shared` and one `--disable-static`; static has one
  `--disable-shared` and one `--enable-static`.
- Exact-snapshot W3 r11 completed on `10.62.148.108:2222`: shared/static
  `conan create` both returned RC0, upstream tests were `0/0`, and the two
  consumer programs both passed (`2/2`).
- Exact W0 evidence: `reports/W0-report.md` and
  `E:/HarmonyPC/validation/libxrender-0.9.12/w0-20260819-r12`.
- W3 r8 confirmed the build-local linker view removes stale dependency `.la`
  paths; configure then required the target `--host=aarch64-linux-ohos` to
  enter cross-compiling mode. Fresh W0 r11 passed after that recipe change.
- Result archive SHA256:
  `2587a0d222d36f84c9f7f77caf9b5e75ff989724df3671da3af5b1438c3d51e4`.
- Official finish r27 ran once on the authorized OHOS endpoint. Its unchanged
  Step 3.5 `setup.sh` and `build_and_test.sh` path passed, generated the real
  `.ci-result.json`, and ran both consumers. The aggregate command retained
  native RC1 because the exact later failure set was `step3, step5b, step7,
  step8`; this is recorded as `W3=PASS`, `aggregate=PARTIAL_POST_W3`, not as an
  aggregate finish pass.
- W3 r7 reached both real `configure` and `make -j1`, but published libtool
  archives carried stale `/storage/Users/currentUser/.conan2` paths. The
  recipe now creates a build-local relocatable linker view; fresh W0 r10
  passed after that recipe change.

## Build design

The recipe uses the release Autotools files and preserves upstream runtime
behavior and ABI. `config.sub` receives a narrow canonical-target patch and
`config.guess` a narrow HarmonyOS/aarch64 recognition patch. The upstream
generated `configure` file is not patched: for OHOS builds the recipe
derives a build-local copy, checks the exact two `umask 077` sites, changes
only those sites to `umask 022`, and configures with the original source tree
as `--srcdir`. The source and retained patch contain no OHOS conditional-
compilation macro.

The retained `config.sub` diff was mechanically generated from a clean source
pair and validated with fuzz=0 dry-run and a byte-identical replay. The
build-local `configure` derivation is fail-closed on the exact occurrence
count. See `reports/PATCH-VALIDATION.md`.

## Dependency boundary

- `libx11/1.8.13`: direct linked dependency.
- `xorgproto/2025.1`: direct public protocol-header dependency.

libXext is not required. The lower X11 closure remains transitive through
libX11.

## Test inventory

The release registers no Automake `TESTS`, `check_PROGRAMS`, `check-local`, or
Meson `test()` entry. The truthful upstream count is therefore 0/0.

The exact-snapshot W3 r11 run executed both installed-package consumers:

1. `libxrender_api_surface` binds all 44 public functions and executes the
   display-independent lowercase `rgba:` parser branch.
2. `libxrender_color_contract` validates channel scaling, alpha
   premultiplication, zero-alpha behavior, and three invalid inputs.

The consumer result is `2/2`.

## Resume condition

The exact-candidate W3 and the official finish W3 substep are closed. The
finish aggregate remains truthfully `PARTIAL_POST_W3` with RC1 and the audited
post-W3 failure set; it must not be relabeled as aggregate PASS. The next gates
are a fresh independent W4 audit and the staged-tree Pre-PR contract.
---

**编译结束**: 2026-08-19 22:21
**最终状态**: built（W3 已通过；官方 finish 为真实 post-W3 部分终态；Pre-PR 待闭合）
