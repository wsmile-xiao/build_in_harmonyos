# linux-headers@5.15 5.15.211 adaptation notes

## Scope

- Package directory: linux-headers@5.15/5.15.211
- Conan reference: linux-headers-5.15/5.15.211
- Upstream source: Linux 5.15.211
- Issue: #812

## Adaptation

- Added a Conan header-library recipe.
- Downloads the Linux 5.15.211 source archive with a pinned sha256. CI #11482
  showed that a direct official kernel.org route can stay connected but remain
  too slow for the 45-minute Conan build timeout, and CI #11528 measured only
  about 11-19KB/s across the direct kernel.org endpoints. `source()` first
  reuses `DOWNLOAD_CACHE`, then tries same-hash authoritative kernel mirrors,
  and keeps canonical kernel.org URLs as fallback.
- Maps Conan `armv8*` variants to the kernel `arm64` name and `x86_64` to the
  kernel `x86` name, while preserving other architecture names.
- Installs sanitized UAPI headers using `make headers_install` with the mapped
  architecture.
- Declares the published `rsync/3.3.0` package as a build tool because the
  upstream `headers_install` target uses rsync for its final include-tree copy.
- Resolves the `rsync/3.3.0` tool requirement from the Conan dependency graph
  and prepends its `bin` directory to PATH for `make headers_install`, so the
  build does not depend on a system-preinstalled `rsync`.
- Packages kernel license text from `COPYING`.

## Tests

- Added `test_package` consumer checks for the installed include layout.
- The test verifies `linux/version.h`, `linux/types.h`, `linux/errno.h`, `asm/unistd.h`, and `asm-generic/unistd.h`.
- The test also verifies version and syscall macros are present.
- The test loads the submitted recipe and checks ARMv8-family and x86_64
  mappings, plus the negative `riscv64` fallback so unsupported architectures
  are not silently rewritten to `arm64`.
- Malformed recipe loading and missing recipe classes produce contextual
  assertions instead of raw tracebacks.
- The test checks the PATH prefix used to expose the packaged `rsync` tool to
  `headers_install`.
- Download timeout/rate overrides accept valid integer values and reject empty,
  non-integer, or out-of-range values with the exact environment variable name.

## Local Validation

- Python syntax validation and repository diff checks pass.
- Native Linux Conan Release and Debug builds run `headers_install`, package
  the generated UAPI tree, and execute the Python and C consumers.
- OHOS-specific results must still come from the supported OHOS environment;
  native Linux evidence is not reported as OHOS validation.
