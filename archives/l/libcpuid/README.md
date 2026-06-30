# libcpuid

A small C library for x86/ARM CPU detection and feature identification. It provides:
- CPU vendor, brand, and model identification
- CPU core and logical processor count detection
- Cache hierarchy information (L1/L2/L3/L4)
- CPU feature flag detection (AES, SHA, SIMD, CRC32, etc.)
- CPU clock frequency measurement (OS-based and RDTSC)
- Raw CPUID data serialization/deserialization
- A command-line tool (`cpuid_tool`) for quick CPU queries

## OpenHarmony ARM64 Compatibility

libcpuid 0.8.0 compiles and runs on OpenHarmony ARM64 (HongMeng Kernel 1.12.0, aarch64, clang 15.0.4, musl libc) with 3 functional patches. **No build-system patches are needed** — using `-DCMAKE_SYSTEM_NAME=Linux` satisfies all cmake conditions (getauxval detection, `_GNU_SOURCE` definition, .so versioning) automatically.

### Build Configuration
```bash
cmake -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_SYSTEM_NAME=Linux \
      -DCMAKE_INSTALL_PREFIX=$PREFIX \
      ..
make -j2 && make install
```

### Functional Patches (0003-0005)
- **0003-cpuid_main.c**: Add `raw_data_t_constructor(data)` in `cpuid_get_raw_data()` to zero the raw data struct, preventing ARM architecture misdetection
- **0004-recog_arm.c**: Set `num_cores=1`, `num_logical_cpus=cpuid_get_total_cpus()`, `total_logical_cpus=cpuid_get_total_cpus()` in `cpuid_identify_arm()`
- **0005-rdtsc.c**: Add ARM clock frequency detection via sysfs cpufreq (`/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq`) and BogoMIPS (`/proc/cpuinfo`)

### Recommended API on ARM
Use `cpu_identify_all()` + `cpuid_get_all_raw_data()` (affinity mode) for correct ARM detection:
```c
#include <libcpuid/libcpuid.h>

struct cpu_raw_data_array_t raw;
struct system_id_t id;
if (cpuid_get_all_raw_data(&raw) == 0 && cpu_identify_all(&raw, &id) == 0) {
    printf("Architecture: %s\n", cpu_architecture_str(id.cpu_types[0].architecture));
    printf("Vendor: %s\n", id.cpu_types[0].vendor_str);
    printf("Cores: %d, Logical: %d\n", id.cpu_types[0].num_cores, id.cpu_types[0].num_logical_cpus);
    printf("Clock: %d MHz\n", cpu_clock_by_os());
}
```

### Important ABI Note
**Do NOT use `LIBCPUID_DISABLE_DEPRECATED` macro in client code.** The library is built with deprecated fields included (default). Using this macro creates a `cpu_id_t` struct size mismatch (9016 bytes vs smaller), causing all ARM fields (implementer, variant, part_num, revision, num_cores, num_logical_cpus) to read from wrong memory offsets.

### Known ARM Limitations
| Field | Value | Reason |
|-------|-------|--------|
| brand_str | "unknown" | ARM has no brand string like x86 |
| code_name / cpu_codename | "unknown" | ARM codename lookup not implemented |
| technology_node | "unknown" | x86-specific field |
| L1/L2/L3 cache sizes | -1 or 0 KB | ARM cache detection not implemented (needs CLIDR_EL1) |
| cpuid_error() | "No error" | Library design: returns string on success, not NULL |

These limitations do not affect core CPU identification functionality.

## Test Results (OpenHarmony ARM64)

| API | Result | Key Data |
|-----|--------|----------|
| cpuid_present() | ✅ PASS | 2048 (HWCAP_CPUID) |
| cpuid_get_total_cpus() | ✅ PASS | 16 logical CPUs |
| cpu_identify() | ⚠️ PARTIAL | ARM ID correct; brand_str=unknown(ARM limitation) |
| cpu_identify_all() | ✅ PASS | cores=1, logical=16 (recommended API) |
| cpu_clock_by_os() | ✅ PASS | 1000 MHz (sysfs cpufreq) |
| serialize/deserialize | ✅ PASS | ARM data preserved correctly |
| ARM feature flags | ✅ PASS | 6+ ARM features detected |
| cpuid_tool --report | ✅ PASS | Full 20-line report |

**Total: 10 PASS / 2 PARTIAL / 0 FAIL**

## Links

- Homepage: https://github.com/anrieff/libcpuid
- License: BSD-2-Clause (see COPYING file in source)
- Version: 0.8.0
