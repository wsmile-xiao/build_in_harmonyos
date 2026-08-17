# btop/1.4.7 OHOS adaptation notes

btop is a C++ terminal resource monitor.  Version 1.4.7 requires C++23 and the
Linux collector reads `/proc` and `/sys`.

## OHOS changes

- Build with upstream Makefile using `PLATFORM=linux`.
- Disable GPU support (`GPU_SUPPORT=false`, `INTEL_GPU_SUPPORT=false`) to avoid
  DRM/ROCm/NVIDIA runtime stacks that are not part of the core CLI validation.
- Avoid the CMake path because it hard-checks several newest C++23 library
  feature macros before compile.  The Makefile path exposes real compiler
  errors instead.
- Add a small `std::expected` fallback header for libc++ builds where `<expected>`
  is unavailable.
- Replace `std::ranges::to` uses with explicit vector construction so the build
  does not depend on the newest ranges-to-container implementation.
- Provide a small `std::ranges` algorithm shim for clang-15 libc++.
- Avoid `pthread_cancel` and `pthread_timedjoin_np` on OHOS.

## Validation plan

- Build/package: `conan create archives/b/btop/1.4.7 --profile=ohos-aarch64 --build=missing`
- Upstream tests:
  1. `cpu_names.amd`
  2. `cpu_names.intel`
  3. `tools.string_split`
- Consumer checks:
  1. `btop --version` reports version `1.4.7`.
  2. `btop --help` prints usage/options text.
  3. `btop --default-config` emits a default configuration containing
     `shown_boxes = "cpu mem net proc"`.

## Validation result

- `conan create archives/b/btop/1.4.7 --profile=ohos-aarch64 --build=missing`: passed.
- Upstream tests: 3/3 passed.
- `test_package/test_btop.sh`: 3/3 assertions passed.
