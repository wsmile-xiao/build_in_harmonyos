# adjtimex

## 软件简介

adjtimex 是一个命令行工具，用于显示或设置内核时间变量（`adjtimex()` 系统调用参数），可显示系统时钟偏差、tick 与频率偏移，并可利用 RTC 做长期漂移校准。

**主要功能**:
- `--print`：显示当前内核时间参数
- `--compare`：比较系统时钟与 RTC，给出校准建议
- `--adjust`：调整系统时钟漂移
- `--version`：输出版本信息

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|----------|--------|
| 1.29 | built ✅ | 2026-08-04 | 2 |

## 适配要点

- 纯 C + Autotools，无第三方 Conan 依赖（仅 musl libc）
- Makefile 要求 `Makefile.in` 在构建目录内 → 只能 in-source 构建
- `bindir=/sbin` 写死 → 改为 `$(prefix)/sbin`；install 移除 `-o root -g bin`
- HMDFS 下 configure 的 `umask 077` 临时目录属主异常 → 改 `umask 002`
- OHOS seccomp 沙箱拦截 `adjtimex()` 系统调用（SIGSYS），运行时 `--print`/调整功能不可用，`--version` 正常
