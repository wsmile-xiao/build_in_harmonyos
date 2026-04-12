# OpenHarmony Compile Agent

> 鸿蒙 (OpenHarmony) 平台开源软件预编译框架
> 版本: v7.0 (Python 全量实现)

## 概述

自动化编译、打包和分发开源软件到 HarmonyOS (OpenHarmony) aarch64 平台。
支持从源码下载到签名打包的完整 13 步编译管线，内置五阶段错误匹配引擎和跨对话恢复机制。

## 快速开始

```bash
# 初始化编译
python3 scripts/ohc-run.py init-build sed 4.9

# 一键全流程（13步）
python3 scripts/ohc-run.py build sed 4.9

# 从失败步骤恢复
python3 scripts/ohc-run.py build sed 4.9 --resume-from=Step3

# 查看编译状态
python3 scripts/ohc-run.py status
```

## 项目结构

```
scripts/
├── ohc-run.py              # 统一 CLI 入口（18 子命令）
├── ohc/                    # Python 包（24 个 .py，零外部依赖）
│   ├── driver.py           # 13 步编译驱动
│   ├── engine.py           # 五阶段错误匹配引擎
│   ├── handoff.py          # HANDOFF 持久化 + 跨对话恢复
│   ├── status.py           # 编译状态扫描
│   ├── graph.py            # 知识图谱 CRUD
│   └── ...                 # 其余 18 个模块
└── _archive_bash/          # 原始 bash 备份（仅供参考）

knowledge/
├── graph/                  # 错误模式知识图谱（E001-E080+）
├── doc/                    # 错误模式文档（E001.md~E080.md）
├── operations/             # 运维知识（打包、环境、调试等 13 篇）
└── principles.yaml         # 编译铁律

archives/                   # 编译档案（30 款 / 33 版本）
references/                 # 参考资料（编译指南、打包规范等 10 篇）
templates/                  # 模板文件（PROGRESS.md, manifest.yaml 等）
```

## CLI 子命令

| 命令 | 说明 |
|------|------|
| `build` | 13 步编译驱动（主入口） |
| `init-build` | 初始化（下载 → 解压 → 骨架 → 环境检查） |
| `finish` | 6 步收尾管线 |
| `engine` | 五阶段错误匹配引擎 |
| `status` | 跨对话编译状态扫描 |
| `handoff` | HANDOFF 上下文输出 |
| `graph` | 知识图谱管理 (add/update/remove/validate) |
| `verify-build` | 4 道质量门禁 |
| `package` | 10 步打包 |
| `sign-elf` | ELF 二进制签名 |
| `refresh-patch` | 补丁生成（difflib） |
| `finalize-archive` | 归档校验 |
| `close-archive` | 关闭归档 |
| `init-archive` | 档案骨架创建 |
| `check-env` | 环境检查 |
| `check-knowledge-gap` | 知识完整性检查 |
| `search-url` | URL 搜索 |
| `summary` | 生成 SUMMARY.md |

## 知识库

### 知识图谱
- **80+ 错误模式** (E001-E080+): 每条含 5 阶段匹配规则、修复方案、鸿蒙特化处理
- **9 条编译铁律** (P-001~P-009): 不变量规则，所有编译必须遵守

### 运维知识 (`knowledge/operations/`)
| 文档 | 说明 |
|------|------|
| `best-practices.md` | 编译最佳实践 |
| `build-systems.md` | 构建系统指南 |
| `debug-methodology.md` | 调试方法论 |
| `dependencies.md` | 依赖管理 |
| `dependency-resolution.md` | 依赖冲突解决 |
| `environment.md` | 环境配置 |
| `filesystem-analysis.md` | 文件系统分析 |
| `harmonyos-specifics.md` | 鸿蒙特化适配 |
| `ohos-adaptation-patterns.md` | 适配模式集 |
| `packaging.md` | 打包规范 |
| `ptrace-alternatives.md` | ptrace 替代方案 |
| `python-extensions.md` | Python 扩展编译 |
| `release.md` | 发布流程 |

### 参考资料 (`references/`)
| 文档 | 说明 |
|------|------|
| `compile-guide.md` | 编译指南 |
| `failure-handling.md` | 失败处理 |
| `iron-rules.md` | 铁律详解 |
| `packaging-guide.md` | 打包指南 |
| `patch-pipeline.md` | 补丁管线 |
| `staging-verify.md` | Staging 验证 |
| `archive-spec.md` | 归档规范 |
| `sudo-analysis.md` | sudo 分析 |
| `design/` | 设计文档 |

## 统计

- **已编译软件**: 30 款 / 33 个版本
- **错误模式**: 80+ 条
- **文档**: 50+ 篇
- **Python 模块**: 24 个（零外部依赖）
- **CLI 子命令**: 18 个

## 设计原则

- **零 bash 依赖**: 所有逻辑纯 Python 实现
- **零外部 Python 依赖**: 仅用标准库
- **跨对话恢复**: HANDOFF 持久化 + status 扫描
- **双轨源码**: .orig（只读基准）+ .work（可写副本）

## 许可证

Copyright (c) 2024-2026 OpenHarmony PC Developer 社区
