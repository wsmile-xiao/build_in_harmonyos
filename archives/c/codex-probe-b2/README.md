# codex-probe-b2

OpenAI-compatible 中转站 / API 网关黑盒纯净度审计 CLI，适用于鸿蒙 PC 平台。

## 简介

`codex-probe`（本包消歧名 codex-probe-b2）是一个纯 Python、零依赖的命令行工具，
用于黑盒判断 OpenAI 兼容 endpoint 是否"纯净"：构建可信基线（baseline）、列出内置
基线、对候选中转站做审计比对，识别模型替换、响应篡改等行为。

## 上游信息

- 项目主页：https://github.com/leiMizzou/codex-probe
- 适配版本：0.0.1（基于 main 分支 commit 579b6b0，与同系列源码包一致）
- 语言：Python 3.10+（requires-python >=3.10）

## 依赖

- Python 3.10+（零外部依赖，标准库实现）

## 已适配版本

- **0.0.1** (2026-09-23) — 纯 Python 应用打包，无编译步骤

## 鸿蒙适配要点

1. 纯 Python 零依赖 CLI：无编译/链接步骤，不产生 ELF，无签名/RPATH 问题
2. PYTHONPATH 注入：conan `runenv_info`/`buildenv_info` 指向包内 `lib/`，
   `cpp_info.bindirs` 指向 `.py` 入口脚本
3. 上游测试套件（unittest，81 项，monkey-patched HTTP 无真实网络）已集成进
   conanfile `build()`，CI 自动执行
