# libmodbus

A Modbus library for Linux, Mac OS X, FreeBSD, QNX and Win32.

- 上游仓库: https://github.com/stephane/libmodbus
- 官方文档: https://libmodbus.org
- 许可证: LGPL-2.1-or-later
- 构建系统: autotools（GitHub tag tarball 无 configure，需 autoreconf 引导）

## 版本索引

| 版本 | 状态 | 构建日期 | 备注 |
|------|------|----------|------|
| 3.1.10 | built | 2026-05-21 | 历史适配 |
| 3.1.12 | built | 2026-05-21 | 历史适配（OHOS config.guess/sub 补丁来源） |
| 3.2.0 | published | 2026-09-09 | 本轮适配：OHOS 平台识别、termios2 检测修复、HMDFS umask 修复、上游测试 3/3 全过 |

## 适配要点（3.2.0）

1. **OHOS 平台识别**（E007）：autoreconf 生成的 config.guess/config.sub 不识别
   `aarch64-unknown-linux-ohos`，继承 3.1.12 的 OHOS 增强版并 chmod +x。
2. **termios2 检测修复**（候选新知识草稿）：`AC_CHECK_TYPES([struct termios2])`
   只查类型，OHOS 有 `struct termios2` 但缺 `TCGETS2/TCSETS2` 常量 → 改为
   "类型+常量"组合编译检测，OHOS 回退标准 termios 路径。
3. **HMDFS umask 陷阱**（E011/E129）：新版 autoconf 生成 `umask 077 && mktemp`，
   修为 `umask 007`（组成员可写）。
4. **上游测试**：unit-tests.sh（make check）、proxy-tests.sh、random-test 3/3 全过；
   bandwidth 基准可运行；消费者 TCP 端到端测试通过。
