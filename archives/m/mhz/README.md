# mhz — 测量 CPU 有效频率

`mhz` 通过执行一串相互依赖、CPU 无法并行化的指令循环，并用 `CLOCK_MONOTONIC`
计时，反推出 CPU 的有效频率（MHz）。在 x86 上还会同时用 `rdtsc` 报告 TSC 频率；
在 aarch64 上只报告 CPU 频率（`rdtsc` 分支不参与编译）。

## 主要功能

- 测量 CPU 有效频率，输出 MHz。
- 可用 `-i` 只报告整数频率；可用位置参数指定测量行数、预热时间与校准值。

## OHOS 适配要点

- **纯 Makefile 构建**：`make CC=<ohos clang>`；上游 `CC := gcc` 由命令行覆盖。
- **零三方依赖、零补丁**：仅需 libc 的 `clock_gettime`。
- `rdtsc` 仅在 x86 上启用（`HAVE_RDTSC`），aarch64 自动走 `CLOCK_MONOTONIC`。

## 产物

| 路径 | 说明 |
|------|------|
| `bin/mhz` | 测量 CPU 频率的可执行程序 |

## 参考资料

- 上游仓库：<https://github.com/wtarreau/mhz>
- 许可证：MIT
