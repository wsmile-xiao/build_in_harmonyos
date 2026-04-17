# OpenHarmony Compile Agent — 架构文档

> **版本**: v2.0 (Python 全量实现)
> **更新时间**: 2026-04-12
> **状态**: ✅ 全部完成

---

## 一、设计原则

| 原则 | 实现方式 |
|------|---------|
| **零 bash 依赖** | 所有逻辑纯 Python 实现 |
| **零外部 Python 依赖** | 仅用标准库（argparse, asyncio, difflib, filecmp, hashlib, json, pathlib, re, subprocess, tarfile, urllib, zipfile, concurrent.futures） |
| **内部调用闭环** | 模块间通过 import 直接调用，无 subprocess 中间层 |
| **HANDOFF 持久化** | stdout + .handoff.json + .build-status.json 三路输出 |
| **跨对话恢复** | `ohc status` 扫描未完成编译，HANDOFF.json 保留上下文 |
| **双轨源码管理** | .orig（只读基准）+ .work（可写副本） |
| **原子补丁替换** | .patch-staging/ → 验证通过后原子替换 |
| **并行签名** | ThreadPoolExecutor 并行 ELF 签名（max_workers=min(cpu, 8)） |
| **async 并行下载** | asyncio 并行 HEAD 探测多个 URL，按可用性排序下载 |

---

## 二、文件结构

```
scripts/
├── ohc-run.py              # 统一 CLI 入口（18 子命令）
├── ohc/                    # Python 包（24 个 .py）
│   ├── cli.py              # 命令分发（argparse 子命令路由）
│   ├── driver.py           # 14 步编译驱动
│   ├── init_build.py       # 初始化管线（registry→async下载→tarfile解压→骨架→环境检查）
│   ├── finish.py           # 6 步收尾管线
│   ├── engine.py           # 五阶段错误匹配引擎
│   ├── handoff.py          # HANDOFF 标准化输出 + JSON 持久化
│   ├── status.py           # 跨对话状态扫描
│   ├── graph.py            # 知识图谱 CRUD（add/update/remove/validate）
│   ├── verify_build.py     # 4 道质量门禁 G1-G4
│   ├── package_builder.py  # 10 步打包
│   ├── sign_elf.py         # ELF 签名（单文件 + 批量并行）
│   ├── refresh_patch.py    # 补丁生成（difflib + filecmp 替代外部 diff）
│   ├── finalize_archive.py # 归档校验（清理 + RELEASENOTE + 完整性）
│   ├── close_archive.py    # 关闭归档（状态更新 + 元数据）
│   ├── check_env.py        # 环境检查
│   ├── init_archive.py     # 档案骨架创建
│   ├── check_knowledge_gap.py # 知识完整性检查
│   ├── search_url.py       # URL 搜索（5 策略）
│   ├── summary.py          # SUMMARY.md 生成（零 PyYAML 依赖）
│   ├── models.py           # 数据模型（KV/TSV/Manifest/BuildContext 解析）
│   ├── utils.py            # 工具函数（日志/路径检测）
│   ├── __init__.py
│   └── __main__.py
```

---

## 三、CLI 参考（18 个子命令）

通过 `python3 scripts/ohc-run.py <子命令>` 调用。

| 子命令 | 模块 | 说明 |
|--------|------|------|
| `build` | driver.py | 14 步编译驱动（主流程） |
| `init-build` | init_build.py | 初始化（registry→下载→解压→骨架→env-check） |
| `finish` | finish.py | 6 步收尾管线 |
| `engine` | engine.py | 五阶段错误匹配引擎（独立调用） |
| `status` | status.py | 跨对话状态扫描，发现未完成编译 |
| `handoff` | handoff.py | HANDOFF 输出（手动触发） |
| `graph` | graph.py | 知识图谱 CRUD（add/update/remove/validate） |
| `check-env` | check_env.py | 环境检查 |
| `init-archive` | init_archive.py | 档案骨架创建 |
| `close-archive` | close_archive.py | 关闭归档（状态更新 + 元数据） |
| `check-knowledge-gap` | check_knowledge_gap.py | 知识完整性检查 |
| `search-url` | search_url.py | URL 搜索（5 策略） |
| `refresh-patch` | refresh_patch.py | 补丁生成（difflib） |
| `finalize-archive` | finalize_archive.py | 归档校验（清理 + RELEASENOTE + 完整性） |
| `verify-build` | verify_build.py | 4 道质量门禁（G1-G4） |
| `sign-elf` | sign_elf.py | ELF 签名（单文件 + 批量并行） |
| `package` | package_builder.py | 10 步打包 |
| `summary` | summary.py | 生成 SUMMARY.md |

---

## 四、模块清单

### 4.1 核心编排层

| 模块 | 职责 | 关键接口 |
|------|------|---------|
| `driver.py` | 14 步编译驱动，编排整个编译生命周期 | `build(name, version, **opts)` |
| `init_build.py` | 初始化管线：registry 查询 → asyncio 并行探测 → urllib 下载 → tarfile 解压 → 骨架创建 → 环境检查 | `init_build(name, version, **opts)` |
| `finish.py` | 6 步收尾管线：补丁 → 归档 → 门禁 → 校验 → 知识 → 摘要 | `finish(name, version, status)` |
| `cli.py` | 命令分发，argparse 子命令路由 | `main()` |

### 4.2 错误处理与恢复

| 模块 | 职责 | 关键接口 |
|------|------|---------|
| `engine.py` | 五阶段错误匹配引擎：regex → 模糊匹配 → 评分排序 → JSON 输出 | `match_error(log_text)` |
| `handoff.py` | HANDOFF 标准化输出：stdout + .handoff.json + .build-status.json | `emit_handoff(context)` |
| `status.py` | 扫描所有进行中的编译，输出状态摘要 | `scan_status()` |

### 4.3 知识图谱

| 模块 | 职责 | 关键接口 |
|------|------|---------|
| `graph.py` | 知识图谱 CRUD：add/update/remove/validate | `graph_add()`, `graph_update()`, `graph_remove()`, `graph_validate()` |
| `check_knowledge_gap.py` | 检查编译产物的知识完整性 | `check_gap(name, version)` |

### 4.4 质量保证

| 模块 | 职责 | 关键接口 |
|------|------|---------|
| `verify_build.py` | 4 道质量门禁：G1-G4 | `verify(name, version)` |
| `sign_elf.py` | ELF 签名：单文件 + 批量并行 | `sign_elf(filepath)`, `sign_batch(directory)` |

### 4.5 归档与补丁

| 模块 | 职责 | 关键接口 |
|------|------|---------|
| `init_archive.py` | 创建档案骨架 | `init_archive(name, version)` |
| `close_archive.py` | 关闭归档：状态更新 + 元数据 + 条件触发补丁 | `close_archive(name, version, status)` |
| `finalize_archive.py` | 归档校验：清理 + RELEASENOTE + 完整性 | `finalize_archive(name, version)` |
| `refresh_patch.py` | 补丁生成：difflib.unified_diff + filecmp.dircmp → 原子替换 | `refresh_patch(name, version)` |

### 4.6 打包与部署

| 模块 | 职责 | 关键接口 |
|------|------|---------|
| `package_builder.py` | 10 步打包：收集→清理→链接→依赖→RPATH→strip→签名→权限→install.sh→tar.gz | `build_package(name, version)` |
| `summary.py` | 生成 SUMMARY.md（遍历 archives/ + 知识图谱统计） | `generate_summary()` |

### 4.7 辅助模块

| 模块 | 职责 |
|------|------|
| `check_env.py` | 鸿蒙编译环境完整性检查（CC, CXX, CFLAGS, toolchain） |
| `search_url.py` | 5 策略 URL 搜索（GNU FTP → GitHub → freedesktop → 官网 → DuckDuckGo） |
| `models.py` | 数据模型与解析器：KV/TSV/Manifest/BuildContext |
| `utils.py` | 工具函数：日志输出、路径检测 |

---

## 五、内部调用链（模块依赖图）

```
driver.py
  ├─ init_build.py（Step 1）
  │    ├─ check_env.py（Step 7）
  │    ├─ init_archive.py（Step 6）
  │    └─ search_url.py（URL fallback）
  ├─ package_builder.py（Step 9）
  │    └─ sign_elf.py（Step 7）
  └─ finish.py（Step 11）
       ├─ refresh_patch.py（Step 1）
       ├─ close_archive.py（Step 2）
       │    └─ refresh_patch.py（条件触发）
       ├─ verify_build.py（Step 3）
       ├─ finalize_archive.py（Step 4）
       ├─ check_knowledge_gap.py（Step 5）
       └─ summary.py（Step 6，import 直调）

engine.py（独立模块，被 driver.py 和 graph.py 引用）
handoff.py（独立模块，被 driver.py 引用）
status.py（独立模块，CLI 入口）
graph.py（独立模块，CLI 入口）
models.py（数据模型，被多个模块引用）
utils.py（工具函数，被所有模块引用）
```

---

## 六、数据流

### 6.1 编译主流程

```
源码 tarball
    │
    ▼
init_build.py ──► .build-context + 双轨源码（.orig/ + .work/）
    │
    ▼
driver.py（Step 2-10）
    │  ├─ 失败 → engine.py → handoff.py → .handoff.json + stdout HANDOFF 块
    │  └─ 成功 → 继续下一步
    │
    ▼
package_builder.py ──► packaging/*.tar.gz + install.sh
    │
    ▼
finish.py（6 步收尾）
    │  ├─ refresh_patch.py → patches/*.patch
    │  ├─ close_archive.py → manifest.yaml 更新
    │  ├─ verify_build.py → reports/quality-report.md
    │  ├─ finalize_archive.py → RELEASENOTE.md + 清理
    │  ├─ check_knowledge_gap.py → 知识遗漏报告
    │  └─ summary.py → SUMMARY.md
    │
    ▼
archives/{l}/{name}/{ver}/（完整归档）
```

### 6.2 跨对话恢复

```
对话 A（编译失败）
  driver.py → handoff.py → 写入:
    ├─ .handoff.json（失败原因、知识匹配结果、下一步建议）
    ├─ .build-status.json（全局状态：软件名/版本/当前步骤/时间戳）
    └─ stdout HANDOFF 块（人类可读摘要）

对话 B（恢复编译）
  status.py → 扫描 .build-status.json
    → 发现未完成编译 + 当前步骤
    → 读取 .handoff.json → 获取失败上下文
    → 读取 .build-context → 恢复环境变量
    → driver.py --resume-from=StepN → 继续编译
```

### 6.3 知识图谱交互

```
engine.py（编译时）
  → 读取 knowledge/graph/index.tsv + E*.kv
  → 匹配错误 → 输出 KNOWLEDGE_HIT
  → 写入 .handoff.json

graph.py（AI 手动调用）
  → add: E*.kv + E*.md + index.tsv
  → update: 修改 .kv 字段 + 同步 index.tsv
  → remove: 归档 .kv/.md → 更新 index.tsv
  → validate: 9 项一致性校验
```

---

## 七、未来改进方向

| # | 方向 | 说明 |
|---|------|------|
| 1 | **自动化测试** | 所有模块缺少单元测试，应建立 `tests/` 目录 + pytest |
| 2 | **配置文件化** | verify_build.py 的 g2-tests.conf 可改为 YAML/JSON 配置加载 |
| 3 | **增量编译** | driver.py 支持 `--incremental` 跳过已成功的步骤 |
| 4 | **并行编译** | 无依赖关系的多个软件并行 init + build |
