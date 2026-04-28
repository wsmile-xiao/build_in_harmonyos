# 归档目录结构规范 (Archive Specification)

> 版本: v2.0 | 日期: 2026-04-28 | 状态: 迁移中

## 1. 设计原则

1. **Git 追踪"怎么编译"，不追踪"编译结果"** — 补丁、配置、知识沉淀入 git；二进制产物忽略
2. **软件级做索引+总览，版本级做编译记录+打包产物** — 两层清晰分离
3. **最小文件集** — 每个软件最少 2 个文件（manifest + README），每个版本最少 1 个文件（manifest）
4. **唯一真相源** — 元数据集中在 manifest.yaml，不分散到多个文件
5. **有则保留，无则不创建** — patches/、packaging/、reports/ 只在需要时存在

## 2. 新结构定义

```
archives/{letter}/{name}/
  ├── manifest.yaml              # 软件级元数据 + 版本索引
  ├── README.md                  # 软件描述（是什么、依赖、OHOS 适配要点）
  └── {version}/
      ├── manifest.yaml          # 版本级编译元数据（配置、补丁、状态）
      ├── notes.md               # 版本适配笔记（替代旧的 PROGRESS.md + 版本级 README）
      ├── patches/               # 该版本所需的补丁（有则保留，无则不创建）
      │   └── 0001-xxx.patch
      ├── packaging/             # 仅当有打包产物时存在
      │   └── {name}-{ver}-ohos-aarch64.tar.gz
      └── reports/               # 构建报告（可选，有则保留）
```

### 2.1 软件级文件

#### manifest.yaml（必须）

```yaml
software: cmake
display: "CMake"
description: "Cross-platform build system generator"
category: build-tool              # foundation|build-tool|compress|crypto|db|network|system|doc|gfx|data
homepage: "https://cmake.org"
license: BSD-3-Clause
build_system: cmake               # 常用构建系统（可被版本级覆盖）

# 跨版本通用的 OHOS 适配知识
ohos_adaptation:
  key_points:
    - "需要设置 CMAKE_SYSTEM_NAME=OHOS"
    - "Bootstrap 阶段需 --no-qt-gui"
  common_dependencies:
    - openssl
    - curl

# 版本索引（所有已归档版本，含状态）
versions:
  "3.30.0":
    status: published             # published | built | failed | archived
    build_date: "2026-04-15"
    published_as: cmake           # 在 cmd-pkgs 中发布的软件名（如与目录名不同）
  "3.28.3":
    status: archived
    build_date: "2026-03-20"
```

#### README.md（必须）

内容要求：
- **第一段**：一句话说明软件是什么
- **功能概述**：主要功能列表
- **OHOS 适配**：适配要点、已知问题、与 Linux 的差异
- **依赖关系**：编译依赖和运行依赖
- **参考资料**：官网、源码仓库链接

不包含：
- 版本特定的编译配置（→ 版本级 manifest.yaml）
- 编译过程记录（→ 版本级 notes.md）

### 2.2 版本级文件

#### manifest.yaml（必须）

```yaml
version: "3.30.0"
status: published                 # published | built | failed | archived
build_date: "2026-04-15"

source:
  url: "https://github.com/Kitware/CMake/releases/download/v3.30.0/cmake-3.30.0.tar.gz"
  sha256: "abc..."
  tar_format: tar.gz              # tar.gz | tar.xz | tar.bz2 | zip

build:
  system: cmake                   # autotools | cmake | meson | makefile | custom
  configure_options:
    - "-DCMAKE_BUILD_TYPE=Release"
    - "-DCMAKE_SYSTEM_NAME=OHOS"
  dependencies:
    - openssl/1.1.1w
    - curl/8.19.0
  cc: clang
  cxx: clang++

patches_applied:
  - "0001-bootstrap-ohos-toolchain.patch"

knowledge_gained:
  - "Bootstrap 需要 -- -DCMAKE_SYSTEM_NAME=OHOS"
  - "内嵌 libuv 需要禁用，使用系统 libuv"
```

#### notes.md（推荐）

版本适配笔记，记录该版本的编译过程、遇到的问题和解决方案。
替代旧的 PROGRESS.md，命名更准确地反映内容。

#### patches/（按需）

- 仅存放实际应用的补丁文件
- 无补丁则不创建此目录
- 补丁命名规范：`{seq}-{description}.patch`，如 `0001-fix-config-sub.patch`

#### packaging/（按需）

- 仅当有预编译打包产物时存在
- 产物命名：`{name}-{version}-ohos-aarch64.tar.gz`
- 不需要 install.sh（cmd-pkgs 仓库有公共安装脚本）
- 不需要 .packaged 标记（目录存在即为标记）

#### reports/（按需）

- 构建报告、测试报告等
- 可选，有价值的报告才保留

#### packaging/ 清理规则

- **保留**: `.tar.gz` 打包产物（由 .gitignore 忽略不上传）
- **删除**: `pkg-{name}-{ver}/` 解压目录（临时产物，占空间）
- **删除**: `install-*.sh`（公共安装脚本已替代）
- **删除**: `debug-symbols/`（由 .gitignore 忽略）

### 2.3 notes.md 模板

> 模板文件位于 [`templates/notes.md`](../templates/notes.md)，请参照该文件生成 notes.md。

**章节规则**：
- **必须有**: 编译环境、编译步骤、问题与方案
- **推荐有**: 依赖版本、构建命令（如非标准 configure/make 流程）
- **按需**: 源码修改、验证结果、交付物、注意事项

### 软件级 README.md 章节建议
```
# {软件名}
## 简介（一句话说明是什么）
## OHOS 适配（适配要点、已知问题、与 Linux 的差异）
## 排除与替代（不推荐安装的命令/组件及替代方案，如适用）
## 依赖
## 功能验证
## 参考
```

## 3. 迁移映射（旧 → 新）

| 旧文件 | 处置 | 原因 |
|--------|------|------|
| `{sw}/README.md` | **保留** | 软件描述，需审查内容质量 |
| `{sw}/RELEASENOTE.md` | **合并到 `{sw}/manifest.yaml`** | 版本信息归入 versions 索引，非独立文件 |
| `{sw}/install.sh` | **删除** | cmd-pkgs 已有公共安装脚本 |
| `{sw}/_index.yaml` | **删除** | 索引信息归入 manifest.yaml |
| `{ver}/manifest.yaml` | **保留** | 核心元数据，需审查字段完整性 |
| `{ver}/PROGRESS.md` | **改名为 notes.md** | 语义更准确，记录适配笔记 |
| `{ver}/README.md` | **合并到 notes.md** | 避免和软件级 README 职责重叠 |
| `{ver}/_meta.yaml` | **合并到 manifest.yaml** | 消除冗余元数据文件 |
| `{ver}/patches/` | **保留** | 仅保留实际补丁文件 |
| `{ver}/packaging/` | **保留** | 仅当有产物时 |
| `{ver}/packaging/install-*.sh` | **删除** | 同 install.sh 理由 |
| `{ver}/packaging/pkg-{name}-{ver}/` | **删除** | 解压临时产物，占空间 |
| `{ver}/reports/` | **保留** | 有价值的报告 |
| `{ver}/.handoff.json` | **.gitignore** | 编译流程内部状态，已在 gitignore |
| `{ver}/.knowledge-done` | **.gitignore** | 编译流程内部状态 |
| `{ver}/.verify-passed` | **.gitignore** | 编译流程内部状态 |
| `{ver}/.g0-verified` | **.gitignore** | 编译流程内部状态 |
| `{ver}/.staging-verified` | **.gitignore** | 编译流程内部状态 |
| `{ver}/patches/.patch-staging` | **.gitignore** | 编译流程内部状态 |
| `{ver}/patches/.patch-backup-*/` | **.gitignore** | 编译流程内部状态 |
| `{ver}/packaging/.packaged` | **.gitignore** | 目录存在即为标记 |
| 空壳版本目录 | **删除** | 无实质内容的版本目录 |

## 4. 字段规范

### 4.1 软件级 manifest.yaml 字段

| 字段 | 必须 | 类型 | 说明 |
|------|------|------|------|
| software | ✅ | string | 软件名（小写，与目录名一致） |
| display | ✅ | string | 显示名 |
| description | ✅ | string | 一句话描述 |
| category | ✅ | string | 分类标签 |
| homepage | 推荐 | string | 官网 URL |
| license | 推荐 | string | 开源许可证 |
| build_system | 推荐 | string | 常用构建系统 |
| ohos_adaptation | 推荐 | object | 跨版本适配知识 |
| versions | ✅ | map | 版本索引 |

### 4.2 版本级 manifest.yaml 字段

| 字段 | 必须 | 类型 | 说明 |
|------|------|------|------|
| version | ✅ | string | 版本号 |
| status | ✅ | string | published / built / failed / archived |
| build_date | ✅ | string | 编译日期 (YYYY-MM-DD) |
| source.url | ✅ | string | 源码下载 URL |
| source.sha256 | 推荐 | string | 源码校验和 |
| source.tar_format | 推荐 | string | 压缩格式 |
| build.system | ✅ | string | 构建系统类型 |
| build.configure_options | 推荐 | list | 配置选项列表 |
| build.dependencies | 推荐 | list | 编译依赖列表 |
| patches_applied | 推荐 | list | 应用的补丁列表 |
| knowledge_gained | 推荐 | list | 编译中学到的知识 |

## 5. 状态定义

| status | 含义 |
|--------|------|
| `published` | 已编译并发布到 cmd-pkgs 仓库 |
| `built` | 已编译成功，尚未发布预编译包 |
| `failed` | 编译失败，记录了失败原因 |
| `archived` | 旧版本，仅保留归档记录 |

## 6. 命名规范

### 目录名
- 软件目录：`{首字母}/{软件名}/`，如 `c/cmake/`
- 版本目录：`{version}/`，如 `3.30.0/`
- 软件名使用小写，与 cmd-pkgs 中的包名保持一致

### 文件名
- 补丁：`{4位序号}-{简短描述}.patch`
- 打包产物：`{name}-{version}-ohos-aarch64.tar.gz`

## 7. 审计结论（2026-04-27）

### 当前问题统计

| 维度 | 问题数 |
|------|--------|
| 空壳/严重残缺目录 | 7 |
| 缺少 install.sh（将删除此要求） | 270 |
| 缺少 packaging/（按需创建） | 250 |
| 缺少 RELEASENOTE.md（将合并到 manifest） | 30 |
| manifest.yaml 字段不完整 | 60+ |
| 编译流程内部状态文件残留 | 大量 |

### 迁移计划

1. **Phase 1 — 基础设施**：更新 .gitignore + 编写本规范 ✅
2. **Phase 2 — 逐软件迁移**：按字母序逐个处理
   - 读取旧文件内容 → 合并到新结构 → 删除冗余文件
   - 每个软件：审查 README.md → 创建软件级 manifest.yaml → 处理版本目录
3. **Phase 3 — 验证**：全量扫描确认所有软件符合新规范
