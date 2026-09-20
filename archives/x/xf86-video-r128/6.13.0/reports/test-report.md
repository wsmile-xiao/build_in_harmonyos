# xf86-video-r128 6.13.0 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 (local device, same profile as CI worker)
- Clang 15 (OHOS SDK)
- Conan 2.29.1 (OHOS adapted)
- Profile: ci/conan/profiles/ohos-aarch64

## Verification

- `conan create archives/x/xf86-video-r128/6.13.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`: exit 0
  - xorg-server SDK provisioned from the official 21.1.15 source release
    (sha256 verified, 295 headers extracted flat into a build-private sdkdir)
  - configure: xorg-server/xproto/fontsproto/randrproto/renderproto/videoproto/xextproto
    all resolved via pkg-config (xorgproto 2025.1, pixman 0.46.4.3,
    libpciaccess 0.19 from the ohpcd registry)
  - DRI/EXA disabled (OHOS xorg-server does not provide them)
  - r128_drv.so built and packaged to lib/xorg/modules/drivers/

## Upstream tests (R51)

- Upstream xf86-video-r128 6.13.0 ships no test suite: no tests/ directory,
  no check-TESTS registrations; `make check` reports "Nothing to be done".

## test_package

Consumer-perspective validation of the packaged driver module:

1. r128_drv.so present under lib/xorg/modules/drivers — PASS
2. Valid ELF64 shared object (magic + e_type ET_DYN) — PASS
3. Module entry point `r128ModuleData` exported — PASS

- Test cases: 3
- Passed: 3
- Failed: 0
- Skipped: 0

## Result

The recipe builds cleanly on the CI profile on device; the driver module is a
loadable X.Org module (loaded by the X server at runtime, so link/run tests
against it are not applicable).
