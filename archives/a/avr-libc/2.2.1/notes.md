# avr-libc 2.2.1 HarmonyOS 适配记录

## 当前状态

- issue: 2240
- branch: `feat/avr-libc-2.2.1-2240`
- 状态: 依赖检查、配方实现、本地前置检查和真机 Shadow CI 均已完成
- 目标: 在 OHOS armv8 主机上生成 AVR 目标端头文件、CRT 对象和静态库

`avr-libc` 不是 OHOS 原生 C 库。产物面向 AVR 微控制器，不能用 OHOS
Clang 构建，也不能作为 OHOS 原生链接库暴露。配方将其作为交叉开发资源打包，
并保持 `cpp_info` 的原生 include/lib/bin 目录为空，仅通过 `resdirs = ["avr"]`
暴露 AVR sysroot。

## W0 依赖检查

2026-08-17 使用项目指定的 OHOS Conan 2.29.1 查询 `ohpcd` 远端时，两个
必需的 AVR 工具包尚未发布。它们遵守“一库一 issue、一分支、一 PR”约束独立
完成适配和真机 CI：

| 依赖 | issue / PR | 真机结果 |
|---|---|---|
| `avr-binutils/2.43.1` | #2244 / #5709 | pass |
| `avr-gcc-bootstrap/14.2.0` | #2245 / #5682 | pass |
| `autoconf/2.72` | 已发布 | 复用 `tool_requires` |
| `automake/1.18` | 已发布 | 复用 `tool_requires` |
| `avrtest` / `simulavr` | 未发布，可选 | 完整模拟执行测试暂缓 |

工具链顺序为 `avr-binutils -> avr-gcc-bootstrap -> avr-libc`。本目录只声明精确
依赖，不包含依赖库源码、补丁或配方。

## 源码和构建系统

- 上游: <https://github.com/avrdudes/avr-libc>
- 版本 tag: `avr-libc-2_2_1-release`
- 配方源: Debian 权威镜像中的对应 orig tag snapshot
- SHA256: `24934244b938b1c265f20e2199cdbe2508b0967635af919883d79ddf39c13b4f`
- 构建系统: Autotools

tag snapshot 包含 `configure.ac`、`Makefile.am` 和 `bootstrap`，但不包含顶层
`configure`。`bootstrap` 会先生成 AVR device/multilib 源码树，再运行
Autoconf/Automake。配方显式使用 `--host=avr`，并从 Conan `tool_requires`
解析全部 AVR 工具，避免交互 shell 中的 `CC` 或 `PATH` 污染构建。

真机上的源码和构建目录位于 HMDFS。适配中解决了以下可复用问题：

- Autotools 包内真实脚本不可执行，改由 HNP Perl/M4 驱动，并修正
  `autoheader -> autom4te` 的派发路径。
- Autoconf 临时目录受 `umask 077` 与 HMDFS 权限语义影响，保留随机目录名，
  使用常规 umask 创建。
- `avr-gcc -B` 需要无前缀的 `as`、`ld`、`nm`，配方从依赖包内构造目标工具
  派发目录，并携带 linker scripts。
- HMDFS 上关闭 Automake dependency tracking，避免依赖文件更新失败。
- 470 个递归目录的完整 multilib 构建使用 `-j4`；单线程在一小时窗口内无法完成。

## 测试策略与结果

上游 `tests/simulate` 共包含 462 个测试源：406 个 C、53 个 C++ 和 3 个汇编。
完整执行依赖 `avrtest` 或 `simulavr`，该独立可选依赖不混入本 PR。现有
`avr-gcc-bootstrap` 是 C-only stage-1 工具链，不提供 `avr-g++` 或 `cc1plus`，
因此 53 个 C++ 源码不能在本轮编译。

本轮使用上游 `runtest.sh -c` 编译、链接其余全部 409 个 C/汇编源码，包括
官方默认的 338 个用例，以及 `util`、`pgmread`、`pgmread-near`、
`pgmread-far` 中的 71 个补充用例。测试 MCU 固定为 `at90s8515`：它使用
bootstrap GCC 已提供的基础 multilib，同时满足 4 个 malloc/realloc 用例的
上游 MCU 条件。结果为 409/409 通过，编译链接通过率 100%；按 462 个源码总量
计算，当前编译链接覆盖率为 88.53%。

`test_package` 使用包内 ATmega328P CRT、`libc.a`、`libm.a` 和设备库编译、链接
实际消费者，再由 `avr-objdump` 和 `avr-nm` 验证 AVR 架构及符号类型：
`memcpy=T`、`strlen=T`、`sin=W`。`sin` 在最终 ELF 中是预期的弱符号。

## 真机 Shadow CI

2026-08-21 在 HarmonyOS/aarch64 真机完成单包 Shadow CI：

```text
run: codex-avr-libc-shadow-ci-r20-2240-requeued-20260821-160012-62802
commit: 55eacfea2a4f0f547f6778b093cfba469024858e
G0=pass L0=pass L1=pass L2=skip L4=pass L5=pass
Build Summary: Total 1, Success 1, Failed 0
```

L2 的非阻断 `skip` 来自文档辅助程序 `avr-man` 不支持 `--version/--help`；
配方关闭文档构建，核心交付物是 AVR sysroot，功能由完整 C/汇编编译链接测试和
`test_package` 覆盖。完整日志和迭代记录见 `reports/shadow-ci.md`。

复现单包 CI：

```sh
CI_PACKAGES="archives/a/avr-libc/2.2.1" zsh ci/conan/build_and_test.sh
```
