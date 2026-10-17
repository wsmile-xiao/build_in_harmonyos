# hdr-histogram（HdrHistogram_c）

[HdrHistogram](https://github.com/HdrHistogram/HdrHistogram_c) 官方 C 移植：高动态范围延迟统计库。
记录延迟/数值到固定粒度指数桶，支持百分位、均值、方差查询与日志编解码（zlib 压缩的 hlog 格式）。

- 上游：https://github.com/HdrHistogram/HdrHistogram_c
- 许可证：CC0-1.0 / BSD-2-Clause
- 构建系统：CMake（纯 C99，零外部重依赖）
- 包类型：library（静态 + 动态，产物 libhdr_histogram.so / libhdr_histogram_static.a）
- 对外目标：`hdr_histogram::hdr_histogram`（CMake）/ `hdr_histogram`（pkg-config）

## OHOS 适配要点

1. `src/hdr_time.c`：OHOS sysroot time.h 缺 `CLOCK_MONOTONIC/CLOCK_REALTIME` 常量——补丁 0001 条件式定义
2. `test/CMakeLists.txt`：`if(UNIX)` 守卫不识别 HarmonyOS——补丁 0003 扩展判定，恢复并发测试注册
3. HDR_LOG（log 组件 + 25 例 log_test）依赖 zlib——conan 工具链不搜 sysroot，配方 generate() 注入 sysroot zlib 路径
4. `hdr_histogram_perf` 长跑性能程序——补丁 0002 加 argc 门控快速路径（--version/--help 安全探测）
5. 共享库无版本名实体，package() 以 patchelf 补 SONAME + 重签（XPM dlopen 要求）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.11.8 | built | 2026-10-02，任务 #14768，64/64 上游用例通过 |

> 注：仓库中另有包名 `hdrhistogram`（无连字符）的独立归档，与本项目同上游不同包名，
> 适配知识互通（见 knowledge/drafts/DRAFT-hdrhistogram-c-0.11.8-sysroot-lib-inject-test-recovery）。
