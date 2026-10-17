# libcpuid-tool

`cpuid_tool` is the command-line CPU identification utility shipped with the
[libcpuid](https://github.com/anrieff/libcpuid) project. It queries the
running CPU and prints vendor, brand, core/logical counts, cache hierarchy,
feature flags, clock estimates and a full report. Unlike the sibling
`libcpuid` package (the shared library), this package ships the end-user
command-line tool only; the internal `cpuid` library is linked statically so
the binary is self-contained.

## OpenHarmony ARM64 Compatibility

libcpuid 0.8.0 builds and runs on OpenHarmony ARM64 (aarch64, clang 15, musl
libc). No build-system patches are needed: forcing `CMAKE_SYSTEM_NAME=Linux`
from the Conan toolchain (knowledge entry E092) satisfies all cmake platform
conditions (`getauxval` detection, `_GNU_SOURCE` via the `UNIX` branch,
versioned `.so` rules) exactly as in the historical `libcpuid` adaptation.

### Build Configuration (this package)
- `BUILD_SHARED_LIBS=OFF`: self-contained static tool binary.
- `LIBCPUID_BUILD_DRIVERS=OFF`: the DKMS branch installs into the absolute
  `/usr/src` prefix, which is not applicable on OHOS.
- `LIBCPUID_ENABLE_DOCS=OFF`: deterministic build without Doxygen.
- `LIBCPUID_BUILD_DEPRECATED` stays `ON` (default).

### Functional Patches (carried over from the historical libcpuid 0.8.0 adaptation)
- **0001-cpuid_main-raw-data-zeroing**: `raw_data_t_constructor(data)` in
  `cpuid_get_raw_data()` prevents ARM architecture misdetection.
- **0002-recog_arm-core-counts**: fill `num_cores`/`num_logical_cpus`/
  `total_logical_cpus` in `cpuid_identify_arm()`.
- **0003-rdtsc-arm-clock-detection**: ARM BogoMIPS and sysfs cpufreq
  fallbacks in `cpu_clock_by_os()`.

### Known ARM Limitations (inherited from libcpuid)
`brand_str`/`code_name`/`technology` print `unknown`, cache sizes report
`-1`/`0`, and `cpuid_error()` returns `"No error"` instead of `NULL`. These
are upstream design limits, not adaptation defects.

## Usage

```console
$ cpuid_tool --version
0.8.0
$ cpuid_tool --report    # full CPU report
$ cpuid_tool --load=dump.txt --report    # replay a raw dump (host independent)
```

## Links

- Homepage: https://github.com/anrieff/libcpuid
- License: BSD-2-Clause
- Version: 0.8.0 (tool binary `cpuid_tool`)
