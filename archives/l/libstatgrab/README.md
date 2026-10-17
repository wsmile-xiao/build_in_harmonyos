# libstatgrab

libstatgrab is a cross-platform C library for obtaining system statistics:
CPU, memory, load, swap, filesystems, disk I/O, network interfaces/traffic,
pages, and processes. It also ships the `statgrab` command-line tool.

- Homepage: https://libstatgrab.org/
- Upstream: https://github.com/libstatgrab/libstatgrab

## OHOS adaptation

- Builds with autotools (configure + make); pure C, no external library deps
- Requires `--build/--host=aarch64-unknown-linux-gnu` since the shipped
  config.guess (2018) does not recognize the HarmonyOS kernel
- OHOS sysroot's `sys/sysinfo.h` and `linux/sysinfo.h` both define
  `struct sysinfo`; include `<linux/sysinfo.h>` and define `_LINUX_KERNEL_H`
  first so `sys/sysinfo.h` keeps only the `sysinfo()` declaration
- OHOS's `linux/ethtool.h` lacks the `ethtool_cmd_speed()` inline (but has
  `speed`/`speed_hi` fields); a local equivalent is provided under `__OHOS__`
- `config.status` uses `umask 077` for its scratch dir; on OHOS restricted
  filesystems writes into that dir are refused, so `umask 022` is used
- cpp_info.libs declares `statgrab` (library file `libstatgrab.a`,
  link flag `-lstatgrab`)

## Test status (OHOS / aarch64)

- Upstream tests: 12 independent API test functions, 10/12 pass (83.3%);
  `fs_stats` returns 0 entries and `disk_io_stats` hits
  `/proc/diskstats` permission denial — both are OHOS sandbox /proc access
  restrictions, not build defects
- HarmonyOS adaptation test (`test_package/test.c` + standalone program):
  sg_init / host_info / mem_stats / load_stats / cpu_stats all PASS

## References

- https://github.com/libstatgrab/libstatgrab
