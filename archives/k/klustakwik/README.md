# klustakwik — 软件归档

本目录包含 KlustaKwik 的鸿蒙适配归档。

## 软件信息

| 字段 | 值 |
|------|-----|
| 软件 | KlustaKwik（MaskedKlustaKwik）3.0.2 |
| 类型 | 纯 C++ spike-sorting 聚类命令行工具（Makefile 构建） |
| 上游 | SourceForge maskedKlustaKwik 目录（官方源） |
| 许可证 | GPL-2.0-or-later |
| 依赖 | 无外部依赖（标准 C/C++） |
| 状态 | built |

## 版本列表

| 版本 | 状态 | 说明 |
|------|------|------|
| 3.0.2 | built | Conan v3.0 配方（application）；W3 本地 CI 通过；本机 default profile conan-verify G1-G4 PASS；ohos-aarch64 交叉验证以远程 OHOS CI 为准 |

## 适配要点

- 纯 Makefile、零依赖，无需 configure/补丁。
- OHOS 工具链经 Conan conf 注入 CC/CXX（R33）；产物需 binary-sign-tool 签名。
- 上游无测试，R51 清点如实申报 0 个；test_package 提供 5 项断言（含鸿蒙特有 aarch64 ELF 架构检查）。
