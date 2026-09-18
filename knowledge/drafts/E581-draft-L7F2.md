# E581 — `uname -s` 在鸿蒙返回 `HarmonyOS`：`ifeq ($(SYS),Linux)` 守卫静默漏编内核相关源文件

- **状态**: 草稿（contributor L7F2）
- **严重度**: 3
- **触发工具**: make / configure / clang / gcc / test
- **阶段**: configuration / compilation / testing
- **来源事件**: libpfm4/4.13.0-git106-g3e4031b（SYS=HarmonyOS 时 perf_events PMU 整体缺失）

## 症状

- 构建完全成功，无报错、无告警；
- 功能整块缺失且**只在运行时/测试时才暴露**：libpfm4 的 `PERF_COUNT_*` 通用事件查不到，
  上游 `tests/validate` 的 perf_events 段失败；
- `make -n lib | grep pfmlib_perf_event` 无输出 —— 源文件根本没进编译命令行。

## 根因

Makefile 生态的常见写法：

```make
SYS := $(shell uname -s)
...
ifeq ($(SYS),Linux)
SRCS += pfmlib_perf_event.c pfmlib_perf_event_pmu.c pfmlib_perf_event_raw.c
endif
```

鸿蒙的 `uname -s` 输出 `HarmonyOS`，而鸿蒙的内核接口就是 Linux 的（perf_event 等系统调用、
sysfs 布局一致）。字符串比较因此为假，只在 Linux 下编译的源文件被静默跳过。

## 推荐方案（rec_approach: pass-sys-explicitly）

构建期显式覆盖变量，不改源码、不新增平台宏：

```bash
make SYS=Linux ARCH=aarch64 -j$(nproc) lib
```

libpfm4 实测最小参数集：`SYS=Linux` + `ARCH=aarch64` + `NOPYTHON=y`（后者跳过 SWIG 子工程）。

## 兜底方案（fallback_approach: patch-sys-guard）

当 `SYS` 还被用于安装路径、平台差异分支等无法命令行覆盖的语义时，打补丁让守卫同时接受
`HarmonyOS`。此补丁含平台宏，按 R8 必须在 PR 说明中给出理由。

## 禁止做法

`sed -i` / `perl -i` 就地改 Makefile 或生成文件绕过探测：污染归档源码、无法复现，升级即丢失。

## 验证

```bash
uname -s                                   # HarmonyOS
grep -rn "uname -s" Makefile config.mk      # 找守卫
make -n lib | grep -c pfmlib_perf_event     # 期望：>0（源文件已编入）
```
