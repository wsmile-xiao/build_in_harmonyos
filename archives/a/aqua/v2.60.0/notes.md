# aqua 编译笔记

## 基本信息

- 软件名: aqua
- 版本: v2.60.0
- 类型: go 工具 (prebuilt binary)
- 编译日期: 2026-08-09
- 许可证: MIT

## 源码信息

- 上游仓库: https://github.com/aquaproj/aqua
- Release: v2.60.0 (2026-06-09)
- 预编译二进制: aqua_linux_arm64.tar.gz
- SHA256: 695e04849161feced95cda06f37f8032287168b19b6eebf2c75c8fe0069e23d1
- 大小: ~7.9 MB

## 编译方式

使用 aquaproj 官方预编译 linux_arm64 二进制：
- Go linker 在 HarmonyOS 上因 mmap 权限限制无法工作 (EPERM on MAP_SHARED)
- aqua 官方提供 linux_arm64 静态链接二进制
- 下载后使用 binary-sign-tool 进行 ELF 签名以在 OHOS 上执行

## 构建方式变更历史

- 初版: 源码编译 (Go toolchain + go build) — 因 mmap 限制失败
- 迭代: 尝试 OHOS 可写工作区路径 — 仍然不稳定
- 最终: 预编译二进制方式 — 简单可靠，conan-verify 8 道门禁全部通过

## Conan 适配

- package_type: application
- 构建方式: prebuilt-binary (下载 + 解压 + ELF签名)
- 无依赖 (dependencies: [])
- test_package: 验证 aqua --version 输出包含版本号
- commands.json: 已声明 (CLI tool, R38)

## 验证

- 二进制文件: bin/aqua
- 功能验证: aqua --version ✅ (在 OHOS 上 ELF 签名后可执行)
- conan-verify: 8 道门禁全部 PASS
- W3 本地 CI 模拟: PASS

## 制品信息

- 制品包: conan create 生成
- 内容: bin/aqua

## 备注

此软件通过预编译二进制方式适配，Go 源码编译因 HarmonyOS mmap 限制无法进行。
ELF 签名使用 binary-sign-tool 工具（位于 /data/service/hnp/bin/）。
---

**编译结束**: 2026-08-09 04:00
**最终状态**: built
