# jh71xx-tools 0-2021.07.16-git43be3329 适配笔记

## 编译环境

- 构建系统：上游 Makefile（单个 C 源文件）
- 目标平台：HarmonyOS PC / OpenHarmony OHOS
- 目标架构：aarch64（交叉编译）和 x86_64（模拟器）
- 编译日期：2026-09-27
- 依赖：仅 HarmonyOS 系统 C 库；无 Conan 第三方依赖

## 编译步骤

上游 Makefile 通过默认 C 编译规则将 `jh7100-recover.c` 编译为 `jh7100-recover`，并附加 `-Wall`。Conan 配方保留该编译行为，使用 `tools.build:compiler_executables` 指定的 C 编译器、Conan build type，以及 profile 提供的 `tools.build:cflags` 和 `tools.build:exelinkflags`。程序和 MIT 许可证安装到包目录。

## 上游测试盘点

固定源码提交 `43be3329` 没有 `test/`、`tests/` 或 `check` 测试目标；Makefile 只声明 `all` 与 `clean`。因此上游自动测试用例为 0。消费者测试实际执行打包程序的 `--help`，并在 OHOS 上检查 `param get const.ohos.fullname` 返回 HarmonyOS/OpenHarmony 系统标识。测试不会打开串口或发送固件。

## 遇到的问题与解决方案

| 问题 | 处理 |
|---|---|
| 上游工具需要真实 JH7100 UART 才能验证固件传输 | 自动化用例只调用在连接串口前退出的 `--help`，并验证 HarmonyOS 系统属性 |
| 本地 SDK 与 CI 的交叉工具链路径不同 | 配方从 Conan `tools.build:compiler_executables` 读取编译器，并从 profile 读取目标编译/链接参数 |

## 适配测试

- 上游测试：无测试目标或用例可运行。
- Conan x86_64 OHOS 构建：通过；生成 Conan 包并包含程序、许可证和上游 README。
- Conan AArch64 OHOS 交叉构建：通过；`llvm-readelf` 确认 ELF64 `Machine: AArch64`。
- HarmonyOS 模拟器消费者测试：通过；实际运行打包程序 `--help`，并读到 `OpenHarmony-6.0.0.47`。
- Conan 在 Windows 交叉构建时因 `can_run()` 跳过 test_package 执行；同一 `test_cli.sh` 已在 x86_64 模拟器上运行。
- 仓库本地 CI 包装器要求 `zsh`，当前 Windows 环境未安装该命令；Conan 两架构构建和设备侧消费者测试已单独执行。
- WSL 启动被系统拒绝（`E_ACCESSDENIED`），所以无法从 Windows 调用仓库的 zsh 本地 CI 包装器。
- 按规则执行精确 Conan 引用检查时，ohpcd 返回 `system acceleration policy not enabled`；Conan 配方检查确认本包没有第三方 Conan 依赖。

## 上游源码校验

- 源码 URL：`https://codeload.github.com/xypron/JH71xx-tools/tar.gz/43be3329`
- SHA256：`edfd6f3f31c2bd55ec8c36f72cb8ae4058c3f3fb8d9710db3dbb79faaa761814`
- Conan 下载及哈希校验通过。普通 GitHub archive URL 返回的压缩字节与 codeload 不同，因此配方使用固定 codeload URL 和显式 tar.gz 文件名。

## 注意事项

更新操作会写入连接的 JH7100 设备。运行实际传输命令前，使用者需要确认 UART 设备节点、权限及固件文件。
