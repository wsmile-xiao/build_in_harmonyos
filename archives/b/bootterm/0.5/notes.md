# bootterm 0.5 适配笔记

## 编译环境
- 构建系统: makefile（顶层简单 Makefile，无 configure）
- 编译日期: 2026-09-05
- 编译器: clang 15.0.4（OHOS aarch64 原生工具链，同时定义 __OHOS__ 与 __linux__）
- 状态: built

## 编译步骤

```bash
make -j1 CC=clang USR_CFLAGS="-DNO_TCGETS2"   # 产物 bin/bt
```

- Makefile 内部固定赋值 `CC := $(CROSS_COMPILE)cc`、`CFLAGS := ...`，忽略环境变量；
  编译器必须用 make 命令行变量传入（R33：从 Conan conf `tools.build:compiler_executables` 取）。
- 追加编译定义走 Makefile 预留的 `USR_CFLAGS` 追加点，不覆盖上游自身的 -O2/-Wall 等。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 默认构建出现 11 个 termios API 隐式声明警告（tcgetattr/tcsetattr/cfset* /tcsendbreak） | `__linux__` 已定义 → 走 `<asm/termbits.h>` 分支且不含 `<termios.h>`；OHOS musl 下函数无原型 | 传上游自带开关 `USR_CFLAGS=-DNO_TCGETS2`，改含 musl `<termios.h>`，零警告 |
| 2 | `-V` 横幅无 "custom baud rates (TCGETS2)" | OHOS sysroot 的 kernel-uapi `<asm/termbits.h>` 未定义 TCGETS2，自定义波特率在默认构建中本就未启用 | 同上；NO_TCGETS2 构建与默认构建运行时行为完全一致（无功能损失） |
| 3 | 上游 install 目标调 strip 与系统 install 工具 | OHOS 设备 strip/签名策略与 CI 签名流水线（E077）冲突 | package() 手动复制 bin/bt，不做 strip，签名交 CI 后处理 |

## 源码修改

无补丁、无源码修改。平台差异全部通过上游自带的 `NO_TCGETS2` 编译开关解决。

## 依赖版本

无外部库依赖（README 明确 "no other dependency than a basic libc"）。

## 测试统计（四口径）

| 口径 | 数量 | 说明 |
|------|------|------|
| 上游源码静态声明 | 0 | 无 tests/ 目录、无 test*/check* 文件、Makefile 无 test/check 目标（find 全树核对） |
| 上游套件实际执行 | 0 | 上游无自动化测试套件 |
| 跳过/未执行 | 0 | 无 |
| 新增 test_package 消费者测试 | 4 | test_bootterm.py：二进制存在性、-V 版本横幅与许可证、-h 完整用法（含 -l/-b/-V 选项行）、-l 串口表头与退出码 0（无串口环境） |

test_package 通过真实运行打包产物 bt 并断言行为（R34），断言近似总数 4（MANIFEST.yml assertion_count）。

## 验证结果

```bash
./bin/bt -V   # BootTerm 0.5.0 / Copyright (C) 2020-2021 Willy Tarreau，退出码 0
./bin/bt -h   # Usage: bt [options] [/dev/ttyXXX | port#] 全部选项，退出码 0
./bin/bt -l   # 打印 port|age|device|driver|description 表头（无串口时为空表），退出码 0
./bin/bt -p   # 无串口时报错退出 1（预期错误路径）
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/bt | bootterm 0.5 主二进制（约 92 KB，MIT） |

## 注意事项

- 源码内 `VERSION` 默认 "0.5.0"，包版本对齐上游 tag v0.5；`-V` 输出 BootTerm 0.5.0。
- bt 是交互式串口终端，CI/无串口环境下仅验证 -V/-h/-l 等非交互路径；连接真实串口的功能依赖 /dev/tty 设备，属环境限制，test_package 已按行为断言覆盖可运行子集。
- 已知限制：NO_TCGETS2 构建不支持 BOTHER 自定义非标准波特率（OHOS kernel-uapi 头未提供 TCGETS2，与默认构建一致）。
---

**编译结束**: 2026-09-06 01:02
**最终状态**: built
