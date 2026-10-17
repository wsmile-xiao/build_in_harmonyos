# libpfm4 (perfmon2)

Hardware performance counter (PMU) programming library for the Linux `perf_events` interface.
It enumerates PMUs and their events and turns an event name into a `perf_event_attr` encoding,
so tools (perf, PAPI, hardware profilers) do not have to hard-code model-specific tables.

- 上游仓库: https://github.com/wcohen/libpfm4
- 许可证: MIT (Copyright (c) 2002-2006 Hewlett-Packard Development Company, L.P.; 部分文件另有声明，详见 COPYING)
- 构建系统: 纯 Makefile（无 configure / CMake / meson）

## 鸿蒙（OHOS aarch64）适配要点

1. **必须显式传 `SYS=Linux`**。`config.mk` 用 `SYS := $(shell uname -s)` 判断平台，鸿蒙返回
   `HarmonyOS`，而 `lib/Makefile` 以 `ifeq ($(SYS),Linux)` 守卫 `pfmlib_perf_event*.c` 三个源文件。
   不覆盖则构建成功但 `PERF_COUNT_*` 通用事件整块缺失（静默失败）。
2. **公共头 ABI 常量补丁**。上游用 glibc 专属 `__WORDSIZE` 选择 ABI 常量；musl 系 OHOS sysroot
   没有 `<bits/wordsize.h>`，常量会退化成 32 位而结构体仍是 64 位。补丁改为可移植 LP64 判定
   （`__LP64__` / `_LP64` / `__SIZEOF_POINTER__ == 8`），库与消费者视图一致。
3. **上游测试进 CI**。`tests/Makefile` 的 `validate` 始终链接静态 `libpfm.a`，因此可以直接在
   `conanfile.py build()` 内执行；事件表校验（含 ARM64 段）成为构建门禁。

## 消费方式

```python
# conanfile.py
def requirements(self):
    self.requires("libpfm4/4.13.0-git106-g3e4031b")
```

```cmake
find_package(libpfm4 REQUIRED)
target_link_libraries(app PRIVATE libpfm4::libpfm4)
```

```c
#include <perfmon/pfmlib.h>
pfm_initialize();
pfm_get_event_encoding("PERF_COUNT_HW_CPU_CYCLES", PFM_PLM0 | PFM_PLM3, &err, &attr, &fstr);
```
