# adamstark-audiofile 1.1.4 HarmonyOS PC W3 Report

- Date: 2026-08-06
- Device: `currentUser@10.62.148.108:2222`
- Device kernel: `HarmonyOS localhost HongMeng Kernel 1.12.0 #1 SMP Tue Apr 28 07:33:02 UTC 2026 aarch64 Toybox`
- Remote W3 root: `/storage/Users/currentUser/ohpcd-w3-adamstark-audiofile-1.1.4-r2-55fc5857`
- Local evidence root: `E:\HarmonyPC\validation\adamstark-audiofile-1.1.4\w3-device-r2`
- Recipe input commit: `55fc5857fa3ec35e8bba4a750a43b67255c6f9bd`
- Recipe input tar size: 20480 bytes
- Recipe input tar SHA-256: `9edf843e0f4747992182e9d92e47f360b354715e22331d245dbd1b3ba3e8e7c3`
- W3 runner SHA-256: `3ecfb4531d0ab62e6e38d709fd5325637196acd5f0fb31e6bfef6cfb466d3632`
- Conan create log SHA-256: `b7f71c7e21568e2763653598aaf7a4b5b44241b39dbf37ad58c54ec275689c8b`

## Environment

- Conan: 2.29.1
- CMake: 4.1.2
- Ninja: 1.13.1
- Clang: 15.0.4
- Conan home: `/storage/Users/currentUser/ohpcd-w3-adamstark-audiofile-1.1.4-r2-55fc5857/conan-home`
- Profile: OHOS 6.0, armv8, clang 15, libc++, C++17
- Jobs: `tools.build:jobs=1`, `CMAKE_BUILD_PARALLEL_LEVEL=1`, `CTEST_PARALLEL_LEVEL=1`, `MAKEFLAGS=-j1`

## Command

```bash
conan create \
  /storage/Users/currentUser/ohpcd-w3-adamstark-audiofile-1.1.4-r2-55fc5857/work/archives/a/adamstark-audiofile/1.1.4 \
  -pr:h=/storage/Users/currentUser/ohpcd-w3-adamstark-audiofile-1.1.4-r2-55fc5857/profile-ohos \
  -pr:b=/storage/Users/currentUser/ohpcd-w3-adamstark-audiofile-1.1.4-r2-55fc5857/profile-ohos
```

## Result

- Exit code: 0
- Recipe revision: `a7ff7212e3c9eff7a817eb10b20e0466`
- Package ID: `da39a3ee5e6b4b0d3255bfef95601890afd80709`
- Package revision: `163be1880246bb6a40d3ed732d0afd83`
- Upstream CTest entry on device: 1/1 passed
- Consumer CTest entry on device: 1/1 passed
- Consumer executable run on device: passed

The upstream CTest entry is the official doctest executable. Host upstream
inventory validation counted 73 doctest test cases and 1,739,931 assertions;
the public upstream test total remains 73/73, with assertions recorded only as
supporting detail.

## Notes

The recipe input tar contains the Conan build inputs (`conanfile.py`,
`conandata.yml`, and `test_package/`) from commit `55fc5857...`. This report was
updated after the device run; no Conan build input changed during the report
refresh.

CMake printed `Problem parsing /proc/meminfo` during configure. It did not
change the final result: configure, build, upstream CTest, install, consumer
CTest, and direct consumer execution all completed successfully.
