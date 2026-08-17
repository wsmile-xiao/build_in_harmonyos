# avr-libc 2.2.1 HarmonyOS 前置适配记录

## 当前状态

- issue: 2240
- branch: `feat/avr-libc-2.2.1-2240`
- 状态: W0 已完成，等待独立依赖包 #2244 与 #2245 的真机 shadow CI
- 目标: 在 OHOS armv8 主机上生成 AVR 目标端头文件、CRT 对象和静态库

`avr-libc` 不是 OHOS 原生 C 库。产物面向 AVR 微控制器，不能用 OHOS
clang 构建，也不能作为 OHOS 原生链接库暴露。配方将其作为交叉开发资源打包，
并保持 `cpp_info` 的原生 include/lib/bin 目录为空。

## W0 依赖检查

2026-08-17 使用项目指定的 OHOS Conan 2.29.1 查询 `ohpcd` 远端：

| 依赖 | 结果 | 处理 |
|---|---|---|
| `avr-binutils/2.43.1` | 未发布 | issue #2244 独立分支、独立 PR 适配 |
| `avr-gcc-bootstrap/14.2.0` | 未发布 | issue #2245 独立分支、独立 PR 适配 |
| `autoconf/2.72` | 已发布 | `tool_requires` |
| `automake/1.18` | 已发布 | `tool_requires` |
| `avrtest` / `simulavr` | 未发布，可选 | 完整模拟执行测试暂缓 |

工具链顺序为 `avr-binutils -> avr-gcc-bootstrap -> avr-libc`。本分支只声明精确
依赖，不包含依赖库源码或补丁。GCC 14.2.0 与 Binutils 2.43.1 均在独立 issue
中适配并分别执行真机 shadow CI。

## 源码和构建系统

- 上游: <https://github.com/avrdudes/avr-libc>
- 版本 tag: `avr-libc-2_2_1-release`
- 配方源: Debian 权威镜像中的对应 orig tag snapshot
- SHA256: `24934244b938b1c265f20e2199cdbe2508b0967635af919883d79ddf39c13b4f`
- 构建系统: Autotools

源码包已在本机下载、校验并解压。tag snapshot 包含 `configure.ac`、
`Makefile.am` 和 `bootstrap`，但不包含顶层 `configure`；`bootstrap` 先生成
AVR device/multilib 源码树，再运行 Autoconf/Automake。配方显式使用
`--host=avr`，并从 Conan `tool_requires` 的 package folder 解析全部 AVR 工具，
避免交互 shell 中的 `CC` 或 `PATH` 污染构建。

## 测试策略

上游 `tests/simulate` 共包含 462 个 C/C++/汇编测试源。完整执行依赖
`avrtest` 或 `simulavr`，不混入本 PR。构建阶段先执行三个代表性用例的官方
compile/link 路径：

- `string/strcmp.c`
- `stdlib/atoi-1.c`
- `math/cos-01.c`

`test_package` 面向 ATmega328P，使用包内 CRT、`libc.a`、`libm.a` 和设备库
编译链接实际消费者，再由 `avr-objdump` 与 `avr-nm` 验证 AVR 架构及
`memcpy`、`strlen`、`sin` 符号。AVR ELF 不会在 OHOS 主机上执行。

## 下一步真机与 shadow CI

依赖包按 #2244、#2245 顺序通过后，使用全局 runner 单包执行：

```sh
sh "$HOME/bin/ohos-test-runner.sh" \
  --user codex --lib avr-libc --task shadow-ci-2240 \
  --mode heavy --try-lock -- \
  sh /path/to/run-ohos-shadow-ci.sh archives/a/avr-libc/2.2.1 <shadow-commit>
```

CI 内部单包命令为：

```sh
CI_PACKAGES="archives/a/avr-libc/2.2.1" zsh ci/conan/build_and_test.sh
```

该 multilib 构建按重任务排队，不与其他真机包并发。
