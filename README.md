# OpenHarmony Compile Agent

> 鸿蒙 (OpenHarmony) 平台开源软件预编译框架
> 版本: v7.8 (Python 全量实现 · 多 Agent 协作 · 知识图谱驱动)

## 加入项目
[邀请链接](https://gitcode.com/invite/link/afd045a86cd9425aa888)， 您可以在点击后通过issue告知我们

快速部署引导，在鸿蒙终端命令行中执行以下命令：
```
wget https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/releases/download/init/setup_wizard.sh && chmod 777 ./setup_wizard.sh && ./setup_wizard.sh
```

## 概述

自动化编译、打包和分发开源软件到 HarmonyOS (OpenHarmony) aarch64 平台。
支持从源码下载到签名打包的完整 13 步编译管线（含预编译风险扫描），内置五阶段错误匹配引擎、跨对话恢复机制和多 Agent 协作模式。

### v7.8 新特性

- **归档规范 v2.0**: 两层结构（软件级 + 版本级），manifest.yaml 唯一真相源，notes.md 替代 PROGRESS.md
- **知识图谱 100+ 条目**: E001-E104 覆盖 musl/HMDFS/SELinux/构建系统等 6 大类错误模式
- **20 条编译铁律**: principles.kv + principles.yaml 双格式，含 critical/high/medium 分级
- **预编译风险扫描**: 源码展开后自动扫描 musl 缺失函数、HMDFS 限制、构建系统问题
- **多任务编译调度**: `dispatch` 命令支持拓扑排序、分阶段异步子任务派发、批量状态监控
- **依赖预编译包自动解析**: 编译前自动检查依赖，有预编译包直接从 [cmd-pkgs](https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs) 安装
- **多 Agent 协作**: 协作者提交 → 主编审核 → 批准/拒绝，支持多人并行编译
- **提交单系统**: 替代 Git PR 的轻量级提交机制
- **知识图谱草稿**: 协作者写草稿，主编审核后入正式知识库

## 快速开始

```bash
# 初始化编译（自动检查依赖并安装预编译包）
python3 scripts/ohc-run.py init-build sed 4.9

# 一键全流程（13步）
python3 scripts/ohc-run.py build sed 4.9

# 从失败步骤恢复
python3 scripts/ohc-run.py build sed 4.9 --resume-from=Step3

# 查看编译状态
python3 scripts/ohc-run.py status
```

### 依赖管理

```bash
# 查看某软件缺少的依赖
python3 scripts/ohc-run.py resolve-deps wget

# 自动安装缺失的预编译包
python3 scripts/ohc-run.py resolve-deps --install wget

# 列出所有可用预编译包
python3 scripts/ohc-run.py resolve-deps --list-available
```

### 多 Agent 协作

```bash
# 协作者：编译后创建分支并提交 PR
git checkout -b feat/sed-4.9
python3 scripts/ohc-run.py submit --check sed 4.9  # 本地自检
git add archives/s/sed/4.9/ knowledge/graph/draft/
git commit -m "feat: 编译 sed 4.9"
git push origin feat/sed-4.9
# 在 GitCode 创建 PR

# 主编：审核 PR → 平台接受/拒绝 → 本地合并
git fetch origin && git checkout feat/sed-4.9
python3 scripts/ohc-run.py review sed 4.9
# 通过 → GitCode 平台 Merge PR → git pull main
# 拒绝 → GitCode 平台 Close PR
```

详见 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [knowledge/collaboration-tutorial.md](knowledge/collaboration-tutorial.md)。

## 项目结构

```
scripts/
├── ohc-run.py              # 统一 CLI 入口（25 子命令）
├── software-registry.yaml  # 软件元数据注册表（init-build 自动下载）
└── ohc/                    # Python 包（29 个 .py，零外部依赖）
    ├── cli.py              # CLI 子命令注册
    ├── driver.py           # 13 步编译驱动
    ├── pre_scan.py         # 预编译风险扫描引擎
    ├── engine.py           # 五阶段错误匹配引擎
    ├── handoff.py          # HANDOFF 持久化 + 跨对话恢复
    ├── status.py           # 编译状态扫描
    ├── graph.py            # 知识图谱 CRUD（支持 --draft）
    ├── dependency_resolver.py  # 依赖预编译包解析
    ├── dispatch.py         # 多任务编译调度（拓扑排序 + 子任务生成）
    ├── submission.py       # 提交单系统（submit/review/post-merge）
    ├── package_builder.py  # 9 步打包管线
    ├── finish.py           # 6 步收尾管线
    └── ...                 # 其余模块

knowledge/
├── graph/                  # 错误模式知识图谱（E001-E104，99 条）
│   ├── index.tsv           # 主索引（TSV 格式）
│   ├── E001.kv ~ E104.kv   # 条目文件
│   ├── principles.kv       # 20 条编译铁律
│   ├── pre-scan-rules.yaml # 预编译风险扫描规则集（闭环增长）
│   └── draft/              # 草稿区（协作者写入，主编审核）
├── doc/                    # 错误模式文档（E001.md~E104.md，99 篇）
├── error-patterns.md       # 人类浏览的错误模式索引
├── operations/             # 运维知识（打包、环境、调试等 13 篇）
├── collaboration.md        # 多 Agent 协作规范
├── collaboration-tutorial.md  # 协作提交教程
├── principles.yaml         # 编译铁律（YAML 格式）
├── ARCHIVE-SPEC.md         # 归档规范 v2.0
└── MIGRATION-GUIDE.md      # 旧归档迁移手册

archives/                   # 编译档案（276 款软件 / 309 个版本）
  {letter}/{name}/
  ├── manifest.yaml         # 软件级元数据 + 版本索引
  ├── README.md             # 软件描述
  └── {version}/
      ├── manifest.yaml     # 编译元数据
      ├── notes.md          # 适配笔记
      ├── patches/          # 补丁文件
      ├── packaging/        # 打包产物（.tar.gz）
      └── reports/          # 构建报告

references/                 # 参考资料（编译指南、打包规范等 10 篇）
templates/                  # 模板文件（8 个）
  ├── manifest-software.yaml  # 软件级 manifest 模板
  ├── manifest-version.yaml   # 版本级 manifest 模板
  ├── notes.md              # 适配笔记模板
  ├── README.md             # 软件级 README 模板
  ├── apply-patches.sh      # 补丁应用脚本
  ├── build-report.md       # 编译报告模板
  ├── test-report.md        # 测试报告模板
  └── compatibility.md      # 兼容性报告模板
```

## CLI 子命令（25 个）

| 命令 | 说明 | 角色 |
|------|------|------|
| `build` | 13 步编译驱动（主入口） | 协作者 |
| `init-build` | 初始化（下载 → 解压 → 骨架 → 依赖 → 环境检查） | 协作者 |
| `init-archive` | 归档骨架创建 | 协作者 |
| `finish` | 6 步收尾管线 | 协作者 |
| `verify-build` | 4 道质量门禁 | 协作者 |
| `clean-verify` | 干净构建验证 | 协作者 |
| `package` | 9 步打包管线 | 协作者 |
| `sign-elf` | ELF 二进制签名 | 协作者 |
| `refresh-patch` | 补丁生成（difflib） | 协作者 |
| `close-archive` | 关闭归档 | 协作者 |
| `finalize-archive` | 归档校验 | 协作者 |
| `engine` | 五阶段错误匹配引擎 | 协作者 |
| `status` | 跨对话编译状态扫描 | 协作者 |
| `handoff` | HANDOFF 上下文输出 | 协作者 |
| `graph` | 知识图谱管理 (add/update/remove/validate) | 协作者 |
| `resolve-deps` | 依赖预编译包查询/安装 | 协作者 |
| `search-url` | URL 搜索 | 协作者 |
| `check-env` | 环境检查 | 协作者 |
| `check-knowledge-gap` | 知识完整性检查 | 协作者 |
| `track-edit` | 源码编辑追踪 | 协作者 |
| `summary` | 生成 SUMMARY.md | 协作者 |
| `dispatch` | 多任务编译调度（plan/status/objective/script） | 协作者 |
| `submit` | 提交前本地自检 | 协作者 |
| `review` | 本地审核辅助（12 项检查） | 主编 |
| `post-merge` | 合并后重建索引 | 主编 |

## 知识库

### 知识图谱
- **99 条错误模式** (E001-E104): 每条含 5 阶段匹配规则、修复方案、鸿蒙特化处理
- **15 条预扫描规则** (pre-scan-rules.yaml): 源码风险预判，闭环增长
- **20 条编译铁律** (P-xxx): 不变量规则，含 critical/high/medium 分级

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

### 协作知识 (`knowledge/`)
| 文档 | 说明 |
|------|------|
| `collaboration.md` | 多 Agent 协作规范（9 章） |
| `collaboration-tutorial.md` | 协作提交教程（从入门到主编） |

### 参考资料 (`references/`)
| 文档 | 说明 |
|------|------|
| `compile-guide.md` | 编译指南（DESTDIR 路径隔离模式） |
| `failure-handling.md` | 失败处理 |
| `iron-rules.md` | 铁律详解 |
| `packaging-guide.md` | 打包指南（9 步流程） |
| `patch-pipeline.md` | 补丁管线 |
| `staging-verify.md` | Staging 验证 |
| `context-trimming-protocol.md` | 上下文裁剪协议 |
| `sudo-analysis.md` | sudo 分析 |
| `design/` | 设计文档 |

## 预编译包

编译好的软件包通过 [cmd-pkgs 仓库](https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs) 分发，支持一键安装：

```bash
# 示例：安装 pkg-config
curl -fsSL "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh" | sh -s -- pkg-config 0.29.2

# Python 有独立安装源
curl -fsSL "https://gitcode.com/OpenHarmonyPCDeveloper/ohos-python-release/releases/download/installer/install.sh" | sh -s -- 3.12.9
```

## CI 质量体系

CI 流水线对每个包强制执行 5 层质量门禁，保障发布质量：

| 门禁 | 检查内容 |
|------|---------|
| L0 | test_package 结构 + 内容 + MANIFEST 声明 |
| L1 | 上游官方测试 (make check) 真实执行验证 |
| L2 | 烟雾测试 (--version / --help) |
| L4 | 静态安全扫描 (NX/PIE/RELRO) |
| L5 | 产物完整性检查 |

### 相关文档

| 文档 | 说明 | 读者 |
|------|------|------|
| [ADAPTATION_GUIDE.md](docs/ADAPTATION_GUIDE.md) | AI 适配操作手册 (新库适配的唯一入口) | AI / 适配人员 |
| [TEST_QUALITY_SPEC.md](docs/TEST_QUALITY_SPEC.md) | 测试质量规范 (5 层防御门禁详情) | AI / 适配人员 |
| [MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md) | 旧归档软件迁移指南 | AI / 适配人员 |

### conan 配方库

```
archives/<首字母>/<包名>/<版本号>/
├── conanfile.py          # 主配方 (build 方法含 make check)
├── conandata.yml         # 源码 URL + 补丁
└── test_package/
    ├── conanfile.py      # 消费者测试
    ├── MANIFEST.yml      # 上游测试声明
    └── *.c / *.sh        # 测试源文件
```

参考实现: `archives/z/zlib/1.3.1/` (Makefile), `archives/b/bash/5.3/` (Autotools)

## 统计

- **已归档软件**: 276 款 / 309 个版本
- **错误模式**: 99 条（E001-E104）
- **编译铁律**: 20 条
- **预扫描规则**: 15 条（闭环增长）
- **可用预编译包**: 247 款（cmd-pkgs 仓库）
- **文档**: 50+ 篇
- **Python 模块**: 29 个（零外部依赖）
- **CLI 子命令**: 25 个（含 dispatch 多任务调度）

## 设计原则

- **零 bash 依赖**: 所有逻辑纯 Python 实现
- **零外部 Python 依赖**: 仅用标准库
- **DESTDIR 路径隔离**: configure --prefix 使用运行时路径，install 通过 DESTDIR 隔离
- **跨对话恢复**: HANDOFF 持久化 + status 扫描
- **双轨源码**: .orig（只读基准）+ .work（可写副本）
- **依赖优先预编译**: resolve-deps 优先安装 cmd-pkgs 预编译包
- **协作分区隔离**: 7 个文件分区，协作者/主编各司其职
- **预扫描闭环**: 编译新发现自动回填规则集，预判能力持续增长
- **唯一真相源**: manifest.yaml 集中管理元数据，消除冗余文件

## 许可证

Copyright (c) 2024-2026 OpenHarmony PC Developer 社区
