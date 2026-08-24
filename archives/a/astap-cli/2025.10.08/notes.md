# astap-cli 2025.10.08 适配笔记

## 编译环境

- 平台：HarmonyOS PC arm64（`os=OHOS`，`arch=armv8`）
- 构建系统：custom Free Pascal Compiler
- 编译器：Free Pascal Compiler 3.2.2 AArch64
- Conan：2.29.1
- 状态：built

## 上游测试

Debian `astap-cli 2025.10.08-1` 源码包未提供 autopkgtest 或上游自动化测试目标，统计为 `0/0（N/A）`。因此新增 Conan 消费者集成测试，不替换任何上游测试。

## 构建流程

1. 下载并校验 Debian `astap-cli_2025.10.08.orig.tar.gz`。
2. 下载并校验官方 FPC 3.2.2 AArch64 发行包。
3. 对 `ppca64`、`fpcres` 和生成的 `astap_cli` ELF 执行 HarmonyOS 签名。
4. 在上游独立 `astap_command_line.lpr` 工程目录中编译命令行程序。
5. 运行 9 项消费者集成断言，包含确定性 FITS 星场的真实 `-analyse`。

## 适配修改

- `patches/0001-sync-cli-version.patch` 将上游遗留版本常量 `2025.09.29` 同步为 `2025.10.08`。
- 未修改上游测试；上游没有测试用例。

## 验证结果

- `conan create`：通过
- `conan-verify` G1–G4：通过
- 消费者集成测试：9/9（100%）
- W3 本地 CI：通过

## 结束

最终交付仅包含命令行 `astap_cli`，不包含 Lazarus GUI、Qt Widgetset 或 LCL 运行时。
---

**编译结束**: 2026-08-23 19:25
**最终状态**: built
