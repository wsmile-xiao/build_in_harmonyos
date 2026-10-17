# boot-info-script 0.78 adaptation notes

## Scope

- Package: `boot-info-script/0.78`
- Source: `https://github.com/arvidjaar/bootinfoscript/archive/refs/tags/v0.78.tar.gz`
- SHA256: `19780542c78756cee5eaf2327e118472d8d509df93bc7bf60deefa7db5ada80d`

## 软件类型判定（R47 语言预检）

- 上游为纯 bash 脚本工具（单文件 `bootinfoscript`，#!/bin/bash），无 C/C++ 源码、
  无构建系统、无 manifest。lang_detect 将 `.sh` 排除出主体统计后无可统计源文件，
  判为 `other`。
- 处理：按已合入先例 ausweisapp-nftrules/2.5.1 的范式，以 `OHPCD_LANG=other`
  声明任务语言通过预检（`task=other, detected=other` 匹配）。SKILL CI 能力矩阵
  明确"bash 脚本类 ✅ 正常"；同仓库已有 acme.sh（纯 shell）、ccmeta（纯 Shell）
  两个已合入先例。

## 上游测试清点（R51 三步法 · 第一步）

v0.78 源码包全文件清单（已核验）：
- `bootinfoscript`（138KB bash 脚本）
- `README`、`CHANGELOG`、`.gitignore`

无 `tests/` 目录、无 Makefile/CMake 测试目标、无 `.github` 工作流、无测试钩子
与文档声明的测试入口 → **上游测试用例数 = 0**（清点证据：源码包全文件清单 +
GitHub tag v0.78 树）。

## 适配内容

- conanfile.py：`package_type=application`，`build()` 留空（无编译）；
  `package()` 将 `bootinfoscript` 装入 `libexec/boot-info-script/`，并在 `bin/`
  下生成 wrapper。
- wrapper 必要性：OHOS 无 `/bin/bash`（shebang 失效），wrapper 用
  `#!/usr/bin/env sh` 启动，通过 `command -v bash` 定位真实 bash（fallback
  `/data/service/hnp/bin/bash`）后显式执行主脚本。
- commands.json（R38）：CLI 工具声明，`type=tool`，`binary=false`。

## 测试

- 上游测试：0（见上游测试清点）。
- 适配后 test_package（R34 实质调用被测包）：6 项核心断言场景（
  wrapper 与 shell 可执行性 2 项属前置校验，不计入核心断言）——
  1. `libexec/boot-info-script/bootinfoscript` 存在
  2. `--version` 输出含 `version: 0.78`
  3. `-v` 别名输出含 `version: 0.78`
  4. `--help` 输出含 `Usage Boot Info Script`
  5. `-h` 别名输出含 `Usage Boot Info Script`
  6. PATH 查找调用 wrapper 输出含 `version: 0.78`
  （MANIFEST assertion_count=6，与核心断言场景一一对应）
- 本地实测：`--version`/`-v`/`--help`/`-h` 均 rc=0 正常输出；
  `--stdout` 完整报告需 root 权限与 fdisk/filefrag 等系统工具（上游设计行为，
  缺失时按脚本逻辑提示并退出 rc=1）。

## 已知限制

- 完整报告生成依赖系统工具（fdisk、filefrag 等）与 root 权限，属上游脚本
  设计行为，非适配缺陷。
- 纯 bash 工具无二进制产物，conan 包内为脚本 + wrapper。

## Local validation

- 本地 `bash bootinfoscript -v/-V/--version/-h/--help` 通过。
- test_package 脚本已在本地手工验证（详见操作日志）。
---

**编译结束**: 2026-09-07 04:28
**最终状态**: built
