# xwininfo 1.1.7 HarmonyOS adaptation notes

## Source and build

- Upstream: https://gitlab.freedesktop.org/xorg/app/xwininfo
- Official release archive: `xwininfo-1.1.7.tar.xz`
- SHA-256: `bee14d594cc86cc59aae1015c1b452a71bf60c304131e2716ca1cf0df733b4ac`
- Build system: autotools; the release includes a generated `configure` script. The source also includes Meson metadata.
- The bundled `config.sub` recognizes `linux-ohos`; the recipe pins the native `aarch64-unknown-linux-ohos` build/host tuple.
- Dependencies follow the X.Org client-tool track: `libxcb/1.16`, `libx11/6.4.0`, and `xorgproto/2025.1`; `libxau/1.0.11` and `libxdmcp/1.1.5` supply the runtime closure.

## Upstream tests

The tagged source has 0 registered upstream tests. `Makefile.am` has no `TESTS`, `check_PROGRAMS`, or `check-local` registrations; `meson.build` has no `test()` declaration; the release tree has no `tests/` or `test/` directory. The build still runs Automake's generated `make check` target, which has no test cases.

## HarmonyOS consumer test

`test_package/test_xwininfo.sh` executes the packaged, signed `xwininfo` ELF under Conan's runtime environment. It checks help output, exact version output, and a read-only root-window query with `DISPLAY` unset. The final case accepts either a successful root-window report when a display is available or the upstream `unable to open display` / `unable to parse display name ""` diagnostic when no display is available. No upstream test source is modified.

## HarmonyOS device validation

- Device: HarmonyOS AArch64, `ohos-aarch64`; isolated `CONAN_HOME=/storage/Users/currentUser/work/psj/ch-xwininfo`.
- `conan create` completed with exit code 0 using `tools.build:jobs=2`.
- Upstream `make check`: 0/0 registered tests; no skips. The tagged source has no upstream test registrations.
- HarmonyOS consumer: 3/3 passed (help output, exact version, and read-only `-root` query/no-display diagnostic).
- Package reference: `xwininfo/1.1.7#077a4a8026f2f6d4ab4fd76418a3c55b:019daf8da59d93521a9a92660f8e6f2a8525ab14#29395679f4caf987e835527a30aa9602`.