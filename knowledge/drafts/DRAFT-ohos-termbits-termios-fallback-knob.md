# DRAFT-OHOS-TERMBITS-TERMIOS-FALLBACK-KNOB — OHOS 双宏下 termbits/termios 头选择陷阱：优先上游回退开关 + make 变量注入免补丁

状态: 草稿（路径 B 知识贡献，随 bootterm/0.5 PR #8567 提交） · 2026-09-06 · 触发实例: bootterm 0.5（任务 #6088）

## 错误特征（稳定签名）

```text
src/bt.c:2470:3: warning: call to undeclared function 'tcsendbreak';
  ISO C99 and later do not support implicit function declarations
  [-Wimplicit-function-declaration]
（同类：tcgetattr ×3、tcsetattr ×3、cfsetispeed、cfsetospeed、cfgetospeed、tcsendbreak ×2，共 11 条）
`-V` 横幅缺 "Built with support for custom baud rates (TCGETS2)" 行
```

## 根因（最小复现）

1. OHOS clang（aarch64-linux-ohos）同时定义 `__OHOS__` 与 `__linux__`（`clang -dM -E - | grep` 实测两宏均为 1）。
2. bootterm bt.c:41 `#if defined(__linux__) && !defined(NO_TCGETS2)` → 包含 `<asm/termbits.h>`、放弃 `<termios.h>`。
3. OHOS sysroot 的 termbits 头：有 struct termios 与 ioctl 常量，但无任何 termios 函数原型（→ 11 条隐式声明警告，函数均返回 int，能链接，静默劣化）；且无 `TCGETS2`（→ 自定义波特率分支在默认构建中本来就未启用，`-V` 横幅无该行可证）。

## 已尝试方案

| 方案 | 结果 |
|------|------|
| 默认构建（无开关） | 编译成功但 11 条隐式声明警告；TCGETS2 缺失 |
| 同步包含 `<asm/termbits.h>` + `<termios.h>` | musl 下 struct termios 双重定义（未采纳） |
| **`USR_CFLAGS=-DNO_TCGETS2`（上游自带开关）** | **0 警告，运行时行为与默认构建完全一致，已采纳** |

## 最终方案与验证

```bash
make -j1 CC=<conan-compiler_executables.c> USR_CFLAGS="-DNO_TCGETS2"
./bt -V   # BootTerm 0.5.0 / Copyright ...（退出码 0，无 TCGETS2 横幅行 = 与默认构建等价）
./bt -h   # Usage 全文（退出码 0）
./bt -l   # port|age|device|driver|description 表头，退出码 0
```

test_package 消费者测试 4/4 通过（真实运行打包产物）；conan-verify G0-G4/L2/L4/L5 全过（PR #8567）。

## 适用范围、反例与解除条件

- 适用：串口/终端工具与一切含 termbits-vs-termios 条件包含的 Linux C 代码（picocom/tio/minicom 类）。
- 反例：上游无编译期回退开关 → 不可用本注入法，走 E102/E147/E148 的源码补丁方案。
- 解除条件：OHOS kernel-uapi 头补齐 TCGETS2 后重评，恢复自定义波特率。

## 查重结论（新增价值）

- E102/E147/E148：均为"`__linux__` 条件编译排除 OHOS"的**源码补丁**方案（mmsghdr/cpu_set 系列），无本条目的"头文件选择"病征，也无"上游开关 + make 变量注入"免补丁方案。
- E063：-Werror 场景压制警告，与本条目的"选对头文件根除警告"不同层。
- 结论：无同类条目，新增价值 = 病征识别（隐式声明警告簇 + 版本横幅缺行）+ 免补丁注入手法 + 行为等价性论证。

## 触发实例与验证证据

- bootterm/0.5（任务 #6088，PR #8567）：默认构建 11 警告 → 开关注入 0 警告；test_package 4/4；W3/W4 通过。
