# libam7xxx 0.1.7 on OpenHarmony PC

The recipe packages the core C library from the [official v0.1.7 snapshot](https://git.ao2.it/libam7xxx.git/snapshot/v0.1.7.tar.gz). The SHA-256 is recorded in `conandata.yml`. It uses the published `libusb/1.0.27` dependency. The three device-facing examples are disabled, so FFmpeg and XCB are not required.

## Adaptation

- Upstream's v0.1.7 tag still reports patch version 5 in `CMakeLists.txt`; `source()` corrects it to 7.
- CMake 4 rejects upstream's 2.6 policy minimum; the toolchain specifies a 3.5 policy minimum.
- On HarmonyOS, CMake cannot find `libm` because it has no platform module. The OHOS compiler links a program calling `lroundf` without `-lm`, so the recipe bypasses that lookup on HarmonyOS.
- The remote file system rejects Make's parallel jobserver FIFO. Both library and consumer builds use `-j1`.
- The shared library and the consumer executable are signed with `binary-sign-tool` before native execution.

## Verification

Upstream test inventory: the v0.1.7 snapshot has no `tests/` directory, no `enable_testing()`/`add_test()` or CTest registration, and no test target. Its `examples/` programs exercise attached projector hardware; they are examples rather than an automated suite. Upstream automated tests: 0. The new Conan consumer supplies one native test.

On 2026-10-01, `conan create` completed on the aarch64 HarmonyOS PC using Conan 2.29.1, Clang 15, OHOS 6.0, and the published `libusb/1.0.27` binary. The CMake consumer linked `libam7xxx::libam7xxx`, called `am7xxx_init`, and ran successfully. `llvm-readelf` showed an ELF64 AArch64 shared library with an OHOS `.codesign` section and a `libusb-1.0.so.0` dependency.

The current SSH user cannot read `/dev/bus/usb`; libusb logs `sysfs_get_device_list: opendir devices failed, errno=13` and returns `LIBUSB_ERROR_IO` from `libusb_init`. The consumer accepts this exact error with a null context, as well as a successful initialization and shutdown. USB projector communication remains to be tested with device access permissions and hardware.
