# DRAFT-metamath-standalone-c-cli-ohos-conan：无外部依赖 C 命令行工具的 OHOS 适配路径

> 状态：draft
> 适用范围：无第三方运行时依赖、由多个 C 源文件组成、提供 `bin/` 可执行文件的 CLI 工具
> 来源：metamath 0.198 HarmonyOS AArch64 适配与 shadow CI
> 更新日期：2026-09-14

## 适用场景

上游项目是传统 C 命令行工具，源码归档包含完整 `.c/.h` 文件，但没有生成后的 `configure`、`Makefile` 或自动化测试入口；工具本身不依赖第三方库，目标是以 Conan application 包形式提供给 OHOS 使用。

Metamath 0.198 符合这一形态：上游 README 给出直接编译方式，归档内的 Autotools 文件只服务于可选的上游生成流程，且没有可直接执行的 `make check`。

## 推荐适配路径

### 1. 先确认依赖边界

- 将 libc 视为目标系统运行时能力，不伪造为 Conan 三方依赖。
- 只把真正需要的构建工具放入 `tool_requires`；本例使用 `tools.build:compiler_executables` 获取 Conan profile 提供的编译器。
- 如果源码和许可证都已在固定归档中，不要为了“补齐格式”额外引入依赖库或生成器。

### 2. 在配方中保留可审计的源码输入

- 固定上游 tag 对应的 URL 和 SHA256。
- 上游归档没有生成构建文件时，直接在 `build()` 中调用 Conan profile 的 C 编译器。
- 用 `validate()` 区分 Linux 与 OHOS；OHOS 目标至少需要检查 `os`, `arch` 和可用的编译器路径。
- OHOS 交叉编译通常需要同时传递 `--target=aarch64-linux-ohos`、SDK sysroot 和适配 libc 的宏，例如 `-D__MUSL__`；不能只把 DevEco `clang` 的绝对路径当作完整交叉编译配置。

### 3. 按 application 组织包内容

建议安装：

```text
bin/<tool>
share/man/man1/<tool>.1
licenses/<license-file>
```

只要包提供 `bin/` 工具，就应在软件级目录提供 `commands.json`，让 CI 和 hicmd 能够识别版本与可执行文件。该文件应位于：

```text
archives/<letter>/<name>/commands.json
```

而不是版本目录内。

### 4. 设计跨平台 test_package

- 测试输入应离线、最小且确定性；Metamath 使用六条语句的最小数据库验证读取和证明检查。
- 用 `can_run()` 判断主机是否能执行目标二进制：Windows 主机交叉编译 AArch64 OHOS ELF 时跳过本机执行，不把跳过误报为适配失败。
- 主机侧至少验证源码下载、SHA256、交叉编译、包布局和 ELF 架构；设备侧补充真实启动、命令参数和输出断言。
- 不要把上游“没有测试入口”当作不写 `test_package` 的理由；消费者测试是判断包可用性的最低闭环。

## 本地与真机职责划分

| 环境 | 应完成的检查 |
| --- | --- |
| Windows 本机 | 配方语法、元数据、源码下载、SHA256、交叉编译、ELF 架构、包清单 |
| OHOS shadow CI | Conan L0/L1/L2/L4/L5、设备端 test_package、包导入和 CLI 启动 |
| 首次真机复核 | 命令行参数引用、路径处理、真实输出、退出码和运行时加载 |

本例的本机 DevEco `clang` 初始失败是因为没有目标 sysroot；补齐 OHOS target、sysroot 和 libc 宏后交叉编译成功。真机首轮又发现了 CLI 的 `READ` 参数问题，说明“编译成功”不能替代设备端行为验证。

## 关联环境规则

- Makefile、Autotools 或测试脚本需要 `make`、`bash` 等工具时，shadow runner 的 `PATH` 需要包含 `/data/service/hnp/bin`；参见 `DRAFT-ZLIB-SHADOW-CI-HNP-TOOL-PATH`。
- 提供 CLI 可执行文件时，软件级 `commands.json` 是 R38/L0k 门禁的一部分；参见 `DRAFT-pico-sdk-cli-commands-json-r38`。
- 真机运行按单包排队，使用隔离 job 和 `CI_PACKAGES` 限定包范围，避免把环境问题误判为源码问题。

## 验证证据

- Conan 包：`metamath/0.198`
- 真机 shadow CI：L0、L1、L2、L4、L5 全部通过
- 设备端测试：版本、源码读取、全库证明验证均通过
- 包含内容：`bin/metamath`、man page、许可证
- 包引用：`metamath/0.198#4f3ccb712512339b0dd6e1056967e939:6b129b068851896169fae42d399fa922d239ce8a#deadde51504f4ef3de9155c30d56f5cb`
