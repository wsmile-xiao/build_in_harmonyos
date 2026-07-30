# spdx-licenses 3.28.0 — SPDX License List Data

## 概述

SPDX License List 是软件包分发许可证的标准化标识符列表，由 Linux Foundation 的 SPDX 工作组维护。本包是 v3.28.0 版本的官方 JSON 数据包，包含 licenses.json 和 exceptions.json 两个核心数据文件。

## 来源

- 官方仓库：https://github.com/spdx/license-list-data
- 下载 URL：https://github.com/spdx/license-list-data/archive/v3.28.0.tar.gz
- 许可证：CC0-1.0（数据本身采用 CC0 1.0 Universal 发布）

## 上游测试

APKBUILD 标注 `!check` / no test suite。上游没有传统测试套件。
验证通过 test_package 的消费者 smoke test 完成。

## 完整性校验

| 文件 | SHA256 |
|------|--------|
| v3.28.0.tar.gz | 52375a91b28b5f6f3142c4b3a555086482f1e09be68c4fa7fdbf377d37afa340 |
| json/licenses.json | f728c534d8bd1044fc515a2ddb2292be99559021d830bfa3281be0bcd36302ee |
| json/exceptions.json | bd145bb558f44432fcd6f0d7e956ed0124dff72af7641a7cfcb1b557dc390a5b |

## 统计数据（test_package 验证）

- licenseListVersion: 3.28.0
- 许可证总数：727
- 已弃用许可证：32
- 异常总数：84
- 已弃用异常：1（Nokia-Qt-exception-1.1）

## 查询验证

| SPDX ID | 预期 | 结果 |
|---------|------|------|
| MIT | FOUND | PASS |
| Apache-2.0 | FOUND | PASS |
| BSD-3-Clause | FOUND | PASS |
| GPL-2.0-only | FOUND | PASS |
| NOT-A-REAL-SPDX-ID | NOT FOUND | PASS |

## 路径判定

路径 B 知识库扩展候选，最终以官方审核为准。
原因：本库是 SPDX License List 数据/规则清单型库，可沉淀固定版本、hash 完整性、license/exception 查询、异常 ID 失败行为和固定输出比对方法。

## 依赖关系

数据/规则清单型库，无第三方 Conan 前置依赖。
