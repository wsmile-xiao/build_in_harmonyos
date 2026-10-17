# Libcsys (CuboCore)

Libcsys is a small C++/Qt6 library that reports live system resource
information on Linux-like systems: CPU usage/frequencies/load averages, memory
and swap, mounted disks and disk I/O, network I/O, system identity, storage
devices, batteries and power actions. The public API lives in the `csys/*.h`
headers and the built artifact is `libcsys.so`.

- Upstream: https://gitlab.com/cubocore/libcsys
- Version: 5.0.0 (`v5.0.0`)
- License: GPL-3.0-or-later
- Build system: CMake (`project(csys)`, C++17, AUTOMOC)

## API surface

| Header | Purpose |
|--------|---------|
| `csys/fileutil.h` | `FileUtil` helpers to read/write text files and line lists |
| `csys/cpuinfo.h` | `CpuInfo` — core count, per-core usage %, frequencies, load averages |
| `csys/memoryinfo.h` | `MemoryInfo` — RAM and swap totals/free/used |
| `csys/systeminfo.h` | `SystemInfo` — hostname, platform, distribution, kernel, uptime, logs |
| `csys/diskinfo.h` | `DiskInfo` — mounted volumes and disk read/write counters |
| `csys/networkinfo.h` | `NetworkInfo` — received/transmitted byte counters |
| `csys/infomanager.h` | `InfoManager` — aggregates all of the above with time series |
| `csys/battery.h` | `BatteryManager` — UPower batteries (D-Bus) |
| `csys/power.h` | `Power` — suspend/hibernate/reboot/poweroff (logind/ConsoleKit D-Bus) |
| `csys/storageinfo.h` | `StorageManager` — UDisks2 devices and blocks (D-Bus) |

## HarmonyOS PC adaptation

The library is an ordinary Qt6 CMake consumer:

```
find_package(Qt6Core REQUIRED)
find_package(Qt6Network REQUIRED)
find_package(Qt6DBus REQUIRED)
target_link_libraries(csys Qt6::Core Qt6::DBus Qt6::Network)
```

Two packaging details are required for HarmonyOS:

1. `qtbase-sql-dbus/6.11.1` is the dependency, not `qtbase/6.11.1` — only the
   former is built with `FEATURE_dbus=ON` and therefore provides `Qt6DBus`. It
   is packaged with `cmake_find_mode=none`, so the recipe writes
   `conan_cmakedeps_paths.cmake` by hand to put its `lib/cmake` on
   `CMAKE_PREFIX_PATH`.
2. CMake has no `Platform/HarmonyOS` module, so `libcsys.so` would be produced
   without `DT_SONAME` and without the versioned symlink chain. The recipe sets
   `CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG` so the package contains the
   `libcsys.so -> libcsys.so.5 -> libcsys.so.5.0.0` chain with a real SONAME.

`patches/0001-fix-runtime-crashes.patch` fixes three upstream defects that are
exposed on HarmonyOS. Two of them are hard crashes:

- `InfoManager::update()` indexed the CPU-frequency list, which is empty
  whenever `/proc/cpuinfo` has no `cpu MHz` field (the OHOS case) → SIGSEGV;
- `Power::~Power()` used the inverted `while (providers.empty())` condition and
  called `takeFirst()` on an empty list → SIGSEGV whenever no systemd/ConsoleKit
  D-Bus provider is present;
- `SystemInfo::getHostname()` passed the `gethostname()` return value (0 on
  success) as a string length, so it always returned an empty string.

## Validation

The library builds cleanly and a consumer test exercises the installed API at
runtime. Because OHOS has no `cpu MHz` in `/proc/cpuinfo` and no UPower/UDisks2/
logind services, the consumer asserts both the real `/proc`-backed values (CPU
core count, memory totals, uptime, network/disk byte pairs) and the graceful
degradation of the D-Bus classes (empty/`false`, never a crash). See
`5.0.0/reports/test-report.md`.
