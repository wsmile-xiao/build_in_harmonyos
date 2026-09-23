# cracklib

CrackLib 是一个密码强度检查库（纯 C），提供 `FascistCheck()`/`FascistCheckUser()`
公开 API：对候选密码执行字典命中、反转命中、过短、过于规律等检查，返回拒绝原因
或 NULL（通过）。上游同时提供 `cracklib-packer`/`cracklib-unpacker`/
`cracklib-check` 建典与检查工具。

本仓库维护 cracklib 在 HarmonyOS PC (aarch64) 平台的 Conan 配方归档。

## 版本

| 版本 | 状态 | 构建日期 | 说明 |
|------|------|----------|------|
| 2.9.8 | built | 2026-09-16 | 首次适配（autotools，零第三方依赖） |

## 归档

- `2.9.8/` — Conan 配方（conanfile.py + conandata.yml + test_package/）+ 适配笔记 + 测试台账
