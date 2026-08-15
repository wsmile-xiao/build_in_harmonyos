# 编译笔记 — aiven-client 4.16.0

**软件名称**: aiven-client (Aiven.io client library / command-line client)
**版本**: 4.16.0
**上游仓库**: https://github.com/aiven/aiven-client
**许可证**: Apache-2.0
**构建系统**: hatchling（纯 Python src layout: aiven/）

## 软件简介

aiven-client (`avn`) 是 Aiven 官方命令行客户端，提供云服务管理、Kafka topic 操作、
VPC peering、认证令牌等功能。纯 Python 包，无 C 扩展。构建后端 hatchling + hatch-vcs，
sdist 已含生成文件 `aiven/client/version.py`（固定 `__version__='4.16.0'`）。

## 依赖

- 运行时依赖: requests (>=2.2.1 on linux), requests-toolbelt (>=0.9.0), certifi (>=2015.11.20.1)
- 测试依赖: pytest, click (dev)
- 构建依赖: hatchling, hatch-vcs（由 pip build isolation 自动从 pypi.cnb.cool 下载）
- 无 Conan 依赖（纯 Python 包，pip install . 构建）

## 构建方式

```bash
conan create archives/a/aiven-client/4.16.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing -nr
```

- `pip install . --prefix=...`（构建后端 hatchling + hatch-vcs）
- 不带 `--no-build-isolation`：让 pip 自动创建隔离环境并从 pypi.cnb.cool 源下载构建依赖
  （同 pluggy/pyparsing/cfgv 方案）

## 适配说明

1. **纯 Python 无 C 扩展**：构建用 sys.executable（Conan 运行的 Python），不使用 clang。
   conanfile 的 settings 含 os/arch 仅用于 R32 OHOS 平台兼容验证。
2. **PYTHONPATH 导出**：package_info 通过 runenv_info.append_path 导出
   site-packages 路径，供下游消费者和 test_package import aiven。
3. **R32 平台兼容**：conanfile validate() 拒绝非 Linux/OHOS 的 OS。
4. **R33 不依赖 shell 环境变量**：build() 使用 sys.executable（Conan 运行时 Python）。
5. **R34 test_package 实质性测试**：7 项 smoke test 覆盖模块导入/版本/AivenClient 类/
   argx.CommandLineTool/pretty.format_item/speller.suggest/session.get_requests_session。

## ⚠️ W3 阻塞修复（关键！2026-08-12）

**现象**：`finish` 的 W3 本地 CI 模拟（`ci/conan/build_and_test.sh`）失败，
`conan create` 报 `FileNotFoundError`，找不到
`.../.build-cache/predl_cache/2068a5c8_aiven_client-4.16.0.tar.gz`。

**根因**（已实测验证，两处叠加）：

1. **CI pre-download 正则截断 URL**：`build_and_test.sh` 中 pre-download 脚本用正则
   `[^\s"'-]+` 提取源码 URL。该字符类排除了连字符 `-`，因此 PyPI 哈希目录 URL
   `.../aiven_client-4.16.0.tar.gz` 被截断为 `.../aiven_client`。
2. **截断 URL 的下载响应差异**（实测）：
   - 哈希目录 URL 截断后 `curl .../aiven_client` → **http:404 size:359**（S3 NoSuchKey XML），
     359 > 100 阈值 → CI 误判"下载成功"，改写 conandata.yml 为
     `file://.../predl_cache/2068a5c8_aiven_client-4.16.0.tar.gz`（不存在）→ conan create 失败。
   - `/packages/source/` 形式 URL 截断后 `curl .../aiven_client` → **http:404 size:0**，
     0 ≤ 100 → CI 判定"下载失败"，不改写 conandata.yml，conan 直接用官方 URL 下载 → 成功。

**修复**：conandata.yml 改用 PyPI 官方 `/packages/source/` 形式 URL：
`https://files.pythonhosted.org/packages/source/a/aiven-client/aiven_client-4.16.0.tar.gz`
（sha256 与哈希目录 sdist 完全一致，实测 `469f9b9f...`）。这正是 alabaster/carburetor 等
已发布 Python 包使用的 URL 形式（规避了同一 CI 正则 bug）。

**验证**：`conan create` + `ci/conan/build_and_test.sh` 100% 通过（1/1），
`finish` W3 阻塞门禁通过，`.ci-result.json` 由 finish 自动写入。

> 注：该 CI pre-download 正则 bug 对"截断 URL 返回 >100 字节 body"的包触发，
> 属于 CI 脚本层面的已知缺陷（本分支不可修改 ci/），已用 URL 形式规避并记录在
> reports/conan-verify-report.md 与 knowledge/drafts。

## 上游测试验证

```bash
cd .tmp-aiven-client/aiven_client-4.16.0
python3 -m pytest tests/ -v --tb=short
```

结果: **223 passed in 33.41s** — 100% 通过率（3+161+4+28+15+7+5=223），
无失败、无跳过、无网络依赖阻塞（全部 mock 离线测试）。

按文件统计（实测）:

| 测试文件 | 通过 |
|----------|------|
| tests/test_argx.py | 3/3 |
| tests/test_cli.py | 161/161 |
| tests/test_cliarg.py | 4/4 |
| tests/test_client.py | 28/28 |
| tests/test_pretty.py | 15/15 |
| tests/test_session.py | 7/7 |
| tests/test_speller.py | 5/5 |
| **合计** | **223/223** |

详细报告: `reports/test-report.md`

## 文件结构

```
archives/a/aiven-client/4.16.0/
├── conanfile.py           # Conan 配方（hatchling 纯 Python）
├── conandata.yml          # 源码 URL + SHA256（/packages/source/ 官方形式，规避 CI 正则 bug）
├── manifest.yaml          # 软件级元数据 + 版本索引
├── notes.md               # 适配笔记
├── reports/
│   ├── test-report.md         # 上游测试报告（223/223）
│   ├── conan-verify-report.md # conan-verify G0-G4/L2/L4/L5 全通过
│   └── conan-create.log       # conan create 日志
└── test_package/
    ├── conanfile.py       # test_package 配方
    ├── MANIFEST.yml
    └── test.sh            # 7 项 smoke test
```**conan create**: ✅ 通过（W3 门禁），.ci-result.json 由 finish 写入
---

**编译结束**: 2026-08-12 10:10
**最终状态**: built
