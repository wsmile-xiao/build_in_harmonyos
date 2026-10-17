# zbackup 1.5 HarmonyOS PC 移植记录

**日期**: 2026-09-23  
**状态**: built  
**目标环境**: HarmonyOS PC 6.0 ARM64，Clang 15，Conan 2.29.1，profile `ohos-aarch64`

## 移植与构建

| 项目 | 状态 | 记录 |
|------|------|------|
| 上游源码 | ✅ | Debian 原始源码包；使用内容校验一致的 Ubuntu 官方归档镜像，SHA256 记录在 `manifest.yaml` |
| 补丁 | ✅ | 版本信息回退、`sptr` 计数类型修复、Conan OpenSSL CMakeDeps 变量兼容 |
| Conan 配方 | ✅ | `G1–G4` 通过；OHOS ARM64 构建、打包和 consumer 测试通过 |
| OHOS 可执行文件签名 | ✅ | `package()` 对交付的 `bin/zbackup` 去除旧 `.codesign` 段并用 `binary-sign-tool` 签名；未签名 ELF 在本机执行会被拒绝 |
| W3 本地 CI | ✅ | `setup.sh` 通过，`build_and_test.sh zbackup/1.5` 成功，1/1 包通过；工具生成的回执和日志在 `.ci-result.json`、`reports/` |

`finish` 收尾将归档状态设为 `built`。W2 原子性检查通过。G0 clean-verify 未在归档目录找到本地原始 tarball；Conan 使用 `conandata.yml` 中的官方源码镜像完成了干净配方构建。提交预检仍需要发布打包产物和 staging 标记；本次只验证移植和 Conan 包，没有执行发布/暂存流程。

## 上游测试清点（R51）

源码包中有 4 组测试目录：`tests/bundle`、`tests/encrypted_file`、`tests/rolling_hash` 和 `tests/regression`。根 CMake 未注册 CTest；上游 Travis 配置只构建程序，不执行这些独立测试。依照 R51，已在 Ubuntu 24.04 WSL x86_64 安装 Qt 5、qmake、GCC、OpenSSL、protobuf、lzma/lzo 等依赖并逐项运行。测试使用 `conandata.yml` 对应的上游归档，SHA256 为 `344fed4491cb52b6712b03c1d8b1bcf994cfc578ad422cb644502e171585a8f7`。

| 上游测试 | 本次结果 | 原因 |
|----------|----------|------|
| bundle 单元测试 | PASS | Qt 5/qmake 构建并运行成功，退出码 0 |
| encrypted_file 单元测试 | PASS | Qt 5/qmake 构建并运行成功，退出码 0 |
| rolling_hash 单元测试 | PASS | Qt 5/qmake 构建并运行成功，退出码 0 |
| Python regression stress suite | PASS | 80 轮、每轮最多新增 60 项并删除 50 项；使用 100 个固定种子的二进制样本和密码文件，退出码 0 |

三个 QMake 项目的上游 `.pro` 与测试 `.cc` 文件均保持原样。构建时仅在临时源码副本提供兼容层：为上游空 `TARGET` 指定目标名，生成 protobuf C++ 文件，按 1.5 发行源码调整源文件列表，并用临时宏/重载兼容测试代码与发行版 API 的命名及签名差异；使用 C++14 编译。兼容层只用于本次测试，没有进入提交包。四组上游测试全部通过（4/4，100%）。

## 实际测试

Conan `test_package` 在 HarmonyOS VM 上运行了 `zbackup -O help`，明文及密码加密仓库的初始化、备份、恢复，并对恢复数据做 SHA-256 比对，均通过。确定性负载为 1,167,360 字节。

HarmonyOS 专项用例将仓库默认 `tmp` 路径替换为不可用的普通文件，并把 `TMPDIR` 指向 HarmonyOS 可写临时目录；备份/恢复仍成功，原测试文件保留，且临时目录无遗留文件。日志输出：`HarmonyOS TMPDIR override: PASS (HarmonyOS-HongMeng_Kernel_1.12.0-aarch64-64bit)`。

W3 结果为 `L0=pass`、`L1=pass`、`L4=pass`、`L5=pass`，总计 1/1。通用 `--version/--help` 探测不适用于 zbackup 1.5 的命令行格式（返回 L2 skip）；有效的 `-O help` 启动检查在 Conan consumer 用例中通过。

## 适配发现

- Conan CMakeDeps 提供小写 `openssl_*` 变量，上游在 `find_package(OpenSSL)` 后读取 `OPENSSL_*`；补丁仅在旧变量未定义时做兼容映射。
- 上游源码包没有 `.git` 元数据，配方通过 `ZBACKUP_VERSION=1.5` 和 CMake fallback 补丁保留版本信息。
- OHOS 内核不允许运行未签名 ELF；签名步骤已集成在 Conan `package()`，避免将未签名文件作为包交付。
