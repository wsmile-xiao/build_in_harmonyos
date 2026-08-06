# OpenHarmony Compile Agent

> 鸿蒙 (OpenHarmony) 平台开源软件编译兼容性框架
> 版本: v8.7 (Conan 配方体系 · 知识图谱驱动 · 多 Agent 协作)

## 加入项目

[邀请链接](https://gitcode.com/invite/link/afd045a86cd9425aa888)

快速部署引导：
- Agent：AtomCode
```bash
wget https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/releases/download/init/setup_wizard_atomcode.sh \
  && chmod 777 ./setup_wizard_atomcode.sh && ./setup_wizard_atomcode.sh
```
- Agent：OpenDesk
```bash
wget https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/releases/download/init/setup_wizard_opendesk.sh \
  && chmod 777 ./setup_wizard_opendesk.sh && ./setup_wizard_opendesk.sh
```
- 

## 项目概述

自动化编译、固化和分发开源软件到 HarmonyOS (OpenHarmony) aarch64 平台。
基于 Conan 包管理器，支持从源码下载到 Conan 配方生成、验证、上传的完整编译管线，内置五阶段错误匹配引擎和知识图谱系统。

**当前规模**：已收录 **427** 款软件 / **490** 个版本（详见 [SUMMARY.md](SUMMARY.md)）

### v8.7 核心特性

- **Conan 配方体系**：conanfile.py + conandata.yml + test_package/ 三件套，`conan create` 验证 + `conan upload` 发布
- **32 条编译铁律** (R1-R32)：覆盖参数/补丁/链接/源码/协作/打包/自检/Conan 配方/平台兼容
- **知识图谱**：211 错误模式条目 (E001-E211)，五阶段引擎匹配，草稿→审核→正式流转
- **8 道验证门禁** (G0-G4 + L2/L4/L5)：预构建评估→配方完整性→conan create→系统同名库隔离→产物完整性→烟雾测试→安全扫描→基线对比
- **CI 流水线**：纯 shell + conan，PR 校验不上传，合并 main 后自动上传 CNB 制品仓
- **多 Agent 协作**：协作者提交 PR → 主编审核 → 合并，支持多人并行编译
- **OHOS 平台适配**：os=OHOS 枚举、aarch64-linux-ohos triplet、CMAKE_SYSTEM_NAME 映射

## 目录结构

```
scripts/
├── ohc-run.py              # 统一 CLI 入口
├── software-registry.yaml  # 软件元数据注册表
└── ohc/                    # Python 包

knowledge/
├── graph/                  # 知识图谱（index.tsv + E*.kv + drafts/）
├── operations/             # 运维知识（构建系统、依赖管理等）
├── ARCHIVE-SPEC.md         # 归档规范
└── error-patterns.md       # 错误模式浏览入口

archives/                   # 编译档案（427 款软件）
  {letter}/{name}/
  ├── manifest.yaml         # 软件级元数据
  ├── README.md             # 软件描述
  └── {version}/
      ├── conanfile.py       # Conan 配方【CI 输入】
      ├── conandata.yml      # 源码 + 补丁声明【CI 输入】
      ├── test_package/      # Conan 测试【CI 输入】
      ├── patches/           # 补丁文件【CI 输入】
      ├── manifest.yaml      # 编译元数据【AI 元数据】
      ├── notes.md           # 适配笔记【AI 元数据】
      └── reports/           # 验证报告【AI 元数据】

ci/                         # CI 脚本（纯 shell，无 AI）
├── conan/
│   ├── setup.sh            # 环境初始化 + profile + remote
│   ├── build_and_test.sh   # conan create + L4/L5 检查
│   ├── upload.sh           # conan upload（仅 release）
│   └── profiles/ohos-aarch64
└── artifacts/sign.sh       # GPG 签名

references/                 # 参考资料
templates/                  # 模板文件
docs/                       # 规范文档
```

## CLI 命令一览

### AI 工具（scripts/ohc-run.py）

| 子命令 | 用途 |
|--------|------|
| `build` | 13 步编译驱动（含 Conan 配方生成+验证）★ 主入口 |
| `init-build` | 下载/解压/骨架/环境/依赖解析 |
| `conan-init` | 生成 conanfile.py + conandata.yml + test_package/ |
| `conan-verify` | conan create + G0-G4 + L2/L4/L5 + 知识图谱 + 草稿 |
| `finish` | 补丁+归档+conan-verify+校验+知识+摘要（6 步） |
| `engine` / `graph add\|update\|validate` | 知识图谱查询/管理 |
| `resolve-deps [--install]` | 查询/安装预编译依赖 |
| `verify-build` / `refresh-patch` | 门禁复查 / 补丁管线 |
| `status` / `handoff` / `track-edit` | 状态恢复 / 源码追踪 |
| `search-url` / `submit` / `review` | URL 搜索 / PR 自检 / 主编审核 |

### CI 脚本（ci/ 目录，纯 shell，无 AI）

| 脚本 | 用途 |
|------|------|
| `ci/conan/setup.sh` | Conan 环境初始化 + profile + remote |
| `ci/conan/build_and_test.sh` | conan create + L4/L5 检查 |
| `ci/conan/upload.sh` | conan upload 到 CNB 制品仓（仅 release） |
| `ci/artifacts/sign.sh` | GPG 签名（非阻塞） |

## 快速开始

### 环境准备

```bash
# Python 安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- python 3.12.9

# pip 源配置（鸿蒙社区源）
pip3 config set global.index-url https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple
pip3 config set global.trusted-host pypi.cnb.cool

# Conan 安装（OHOS 适配版）
pip3 install conan
```

### 模式 A：Conan 驱动（推荐，适合已有配方的软件）

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py build <软件名> [<版本>]
# → 13 步全自动：init→patches→configure→make→install→conan-init→conan-verify→finish
```

### 模式 B：探索性编译（适合首次/复杂软件）

```bash
# Step 1: 初始化
python3 $SKILL_ROOT/scripts/ohc-run.py init-build <软件名> [<版本>] [--url=URL]

# Step 2: AI 手动编译
source .build-context-<name>-<ver> && cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX && make -j2 && make install DESTDIR=$TEST_PREFIX
make check

# Step 2.5-2.6: 生成并验证 Conan 配方
python3 $SKILL_ROOT/scripts/ohc-run.py conan-init <软件名> <版本>
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify <软件名> <版本>

# Step 3: 收尾
python3 $SKILL_ROOT/scripts/ohc-run.py finish <软件名> <版本> published|built|failed
```

### 依赖管理

```bash
# 查看缺少的依赖
python3 $SKILL_ROOT/scripts/ohc-run.py resolve-deps <软件名>

# 自动安装预编译包
python3 $SKILL_ROOT/scripts/ohc-run.py resolve-deps --install <软件名>

# 列出所有可用预编译包
python3 $SKILL_ROOT/scripts/ohc-run.py resolve-deps --list-available
```

### 预编译包安装

编译好的软件包通过 [cmd-pkgs 仓库](https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs) 分发：

```bash
curl -fsSL "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh" | sh -s -- <软件名> <版本>
```

## 相关文档

| 文档 | 说明 |
|------|------|
| [SKILL.md](SKILL.md) | 主操作手册（v8.7），每次编译前必读 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献指南 |
| [KNOW_YOUR_WHY.md](KNOW_YOUR_WHY.md) | 核心设计理念与约束 |
| [docs/ADAPTATION_GUIDE.md](docs/ADAPTATION_GUIDE.md) | AI 适配操作手册（新库适配入口） |
| [docs/TEST_QUALITY_SPEC.md](docs/TEST_QUALITY_SPEC.md) | 测试质量规范（5 层防御门禁） |
| [references/iron-rules.md](references/iron-rules.md) | 32 条铁律详解 |
| [SUMMARY.md](SUMMARY.md) | 软件兼容性总览（自动生成） |

## 许可证

Copyright (c) 2024-2026 OpenHarmony PC Developer 社区
