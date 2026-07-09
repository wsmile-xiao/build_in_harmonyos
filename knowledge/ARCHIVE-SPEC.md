# 归档目录结构规范 (Archive Specification)

> 版本: v3.0 | 日期: 2026-06-22 | 状态: 生效
> 
> v3.0 变更: 新增 conanfile.py + conandata.yml + test_package/ 为必填文件，
> conanfile.py 成为 CI 唯一构建输入，manifest.yaml 降级为交叉校验元数据。
> packaging/ 目录废弃（Conan 体系替代手动 tar.gz 打包）。

## 1. 设计原则

1. **Conan 配方是唯一真相源** — `conanfile.py` 定义"怎么编译"，CI 只读它
2. **manifest.yaml 是人读索引** — 交叉校验用，CI 不依赖它
3. **Git 追踪配方和知识，不追踪二进制** — 补丁、配置、知识沉淀入 git
4. **最小文件集** — 每个版本最少 4 个文件（conanfile.py + conandata.yml + manifest.yaml + notes.md）
5. **有则保留，无则不创建** — patches/、reports/ 只在需要时存在

## 2. 新结构定义 (v3.0)

```
archives/{letter}/{name}/
  ├── manifest.yaml              # 软件级元数据 + 版本索引（人读，CI 不依赖）
  ├── README.md                  # 软件描述（是什么、依赖、OHOS 适配要点）
  ├── commands.json              # 命令行工具声明（仅 tool 类型，R38）
  └── {version}/
      ├── conanfile.py           # 【必填·CI唯一输入】可执行 Conan 配方
      ├── conandata.yml          # 【必填】源码URL + SHA256 + 补丁声明
      ├── manifest.yaml          # 【必填·交叉校验】版本编译元数据
      ├── notes.md               # 【必填】适配笔记
      ├── test_package/          # 【必填】Conan L1 官方测试
      │   ├── conanfile.py
      │   └── CMakeLists.txt     # (或 test.c)
      ├── patches/               # 该版本所需的补丁（有则保留，无则不创建）
      │   └── 0001-xxx.patch
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
    conan_ref: "cmake/3.30.0"  # Conan 引用格式
  "3.28.3":
    status: archived
    build_date: "2026-03-20"
```

**模板**：参见 `templates/manifest-software.yaml`

#### README.md（必须）

内容要求：
- **第一段**：一句话说明软件是什么
- **功能概述**：主要功能列表
- **OHOS 适配**：适配要点、已知问题、与 Linux 的差异
- **依赖关系**：编译依赖和运行依赖
- **参考资料**：官网、源码仓库链接

不包含：
- 版本特定的编译配置（→ 版本级 conanfile.py）
- 编译过程记录（→ 版本级 notes.md）

#### commands.json（条件必填·仅 tool 类型，R38）

命令行工具声明文件。当构建产物包含可执行文件（`bin/` 目录下有二进制）时，**必须**在软件级别目录下创建此文件。库类型（只有 `.a`/`.so`）不需要。

**文件位置**：`archives/{letter}/{name}/commands.json`（与 manifest.yaml、README.md 同级）

**格式**：

```json
{
  "name": "strace",
  "description": "系统调用追踪工具，用于诊断和调试程序",
  "homepage": "https://strace.io",
  "type": "tool",
  "versions": {
    "6.19": {
      "ref": "strace/6.19",
      "binary": true
    }
  }
}
```

| 字段 | 说明 |
|------|------|
| name | 包名（与 Conan 包名一致） |
| description | 中文描述（一句话说明功能） |
| homepage | 上游官网 URL |
| type | 固定 `"tool"` |
| versions.{ver}.ref | Conan 引用（`name/version`） |
| versions.{ver}.binary | 是否已发布二进制到制品仓（适配中为 `false`，发布后改为 `true`） |

**判断标准**：
- conanfile.py 中 `package_info()` 设置了 `cpp_info.bindirs`
- conanfile.py 中有 `RUNTIME DESTINATION bin` 或类似可执行文件安装
- conanfile.py 中 `package_type = "application"`

> CI 门禁 L0k 自动校验：工具类型必须有 commands.json，库类型不应有（warn 级别）。

### 2.2 版本级文件

#### conanfile.py（必须·CI唯一构建输入）

可执行的 Conan 2.x 配方。CI 的 `conan create` 读取此文件完成构建。

**必须包含**：
- `name`, `version`, `description`
- `settings = "os", "compiler", "build_type", "arch"`
- `export_sources()` — 导出 conandata.yml 和 patches
- `source()` — 从 conandata.yml 读取源码 URL 并下载
- `build()` — 应用补丁 + 构建编译
- `package()` — 安装到 Conan package 目录
- `package_info()` — 声明 cpp_info.libs（供下游依赖解析）

**强制规则**：
- 终端工具：`generate()` 中必须设置 `BUILD_SHARED_LIBS=OFF`（CMake）或 `-static`（Autotools）或 `default_library=static`（Meson）（R26）
- 依赖引用：`self.requires("name/version")`（R27）
- 补丁应用：`apply_conandata_patches(self)`（从 conandata.yml 读取）
- 禁止 `--build`/`--host`/`--target` 三元组（native 编译，R1）

**模板**：参见 `templates/conanfile-{cmake|autotools|makefile|meson}.py.tmpl`

#### conandata.yml（必须）

源码地址 + SHA256 + 补丁声明的集中管理文件。

```yaml
sources:
  url: "https://curl.se/download/curl-8.15.0.tar.gz"
  sha256: "abc123def456..."

patches:
  "0001-fix-socket.patch":
    patch_file: "patches/0001-fix-socket.patch"
    patch_description: "Fix sockaddr_storage redefinition on HarmonyOS"
    patch_type: "portability"     # portability | bugfix | backport
```

**模板**：参见 `templates/conandata.yml.tmpl`

#### manifest.yaml（必须·交叉校验）

版本编译元数据。CI 不依赖此文件，但它用于：
- 人类快速了解编译状态和配置
- 与 conanfile.py 的版本号、依赖列表交叉校验
- 知识检索入口

```yaml
version: "3.30.0"
status: published                 # published | built | failed | archived
build_date: "2026-04-15"
conan_ref: "cmake/3.30.0"  # Conan 引用

source:
  url: "https://github.com/Kitware/CMake/releases/download/v3.30.0/cmake-3.30.0.tar.gz"
  sha256: "abc..."
  tar_format: tar.gz

build:
  system: cmake
  configure_options:
    - "-DCMAKE_BUILD_TYPE=Release"
  dependencies:
    - openssl/1.1.1w
  cc: clang
  cxx: clang++

patches_applied:
  - "0001-bootstrap-ohos-toolchain.patch"

knowledge_gained:
  - "Bootstrap 需要 -- -DCMAKE_SYSTEM_NAME=OHOS"
```

> **注意**：`source.url`、`source.sha256`、`patches_applied` 应与 conandata.yml 保持一致。
> 出现不一致时以 conandata.yml 为准（它是 CI 的实际输入）。

#### notes.md（必须）

版本适配笔记，记录该版本的编译过程、遇到的问题和解决方案。

**模板**：参见 `templates/notes.md`

#### test_package/（必须）

Conan L1 官方测试。CI 通过 `conan create` 自动执行。

```
test_package/
├── conanfile.py      # 测试配方
└── CMakeLists.txt    # (或 test.c — 简单验证)
```

**模板**：参见 `templates/test_package/`

**最低要求**：
- 编译一个引用该包的简单程序
- 运行该程序验证链接和运行时可用
- 如果是纯库（无 bin/），验证 `find_package` 能找到它

#### patches/（按需）

- 仅存放实际应用的补丁文件
- 无补丁则不创建此目录
- 补丁命名规范：`{seq}-{description}.patch`，如 `0001-fix-config-sub.patch`
- 补丁必须在 conandata.yml 中声明才能被 `apply_conandata_patches()` 应用

#### reports/（按需）

- 构建报告、测试报告等
- conan_verify 的验证报告存放在此
- 兼容性评估报告模板：参见 `templates/compatibility.md`

### 2.3 废弃的文件/目录

| 文件/目录 | 处置 | 原因 |
|-----------|------|------|
| `packaging/` | **废弃** | Conan 体系替代手动 tar.gz 打包 |
| `packaging/*.tar.gz` | **删除** | conan create + conan upload 替代 |
| `packaging/install-*.sh` | **删除** | 公共安装脚本已替代 |
| `packaging/.packaged` | **删除** | 不再需要 |
| `.verify-passed` | **废弃** | 由 conan_verify 替代 |
| `.staging-verified` | **废弃** | Conan 自带隔离验证 |
| `.handoff.json` | **.gitignore** | 编译流程内部状态 |
| `.knowledge-done` | **.gitignore** | 编译流程内部状态 |

## 3. 状态定义

| status | 含义 | 触发条件 |
|--------|------|---------|
| `published` | 已通过 conan verify + conan upload 发布 | conan_verify PASS + conan upload 成功 |
| `built` | conanfile.py 已生成 + conan verify 通过，未上传 | conan_verify PASS，未 upload |
| `failed` | 编译失败或 conan verify 失败 | 探索性编译失败或 conan create 失败 |
| `archived` | 旧版本归档 | 新版本发布后旧版本标记 |

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
| versions.{ver}.conan_ref | 推荐 | string | Conan 引用格式 name/ver |

### 4.2 版本级 manifest.yaml 字段

| 字段 | 必须 | 类型 | 说明 |
|------|------|------|------|
| version | ✅ | string | 版本号 |
| status | ✅ | string | published / built / failed / archived |
| build_date | ✅ | string | 编译日期 (YYYY-MM-DD) |
| conan_ref | 推荐 | string | Conan 引用 (name/ver) |
| source.url | ✅ | string | 源码下载 URL（与 conandata.yml 一致） |
| source.sha256 | 推荐 | string | 源码校验和 |
| source.tar_format | 推荐 | string | 压缩格式 |
| build.system | ✅ | string | 构建系统类型 |
| build.configure_options | 推荐 | list | 配置选项（与 conanfile.py 一致） |
| build.dependencies | 推荐 | list | 编译依赖列表 |
| patches_applied | 推荐 | list | 应用的补丁列表 |
| knowledge_gained | 推荐 | list | 编译中学到的知识 |

### 4.3 conandata.yml 字段

| 字段 | 必须 | 类型 | 说明 |
|------|------|------|------|
| sources.url | ✅ | string | 源码 tarball 下载 URL |
| sources.sha256 | ✅ | string | 源码 SHA256 校验和 |
| patches.{filename}.patch_file | 条件必填 | string | 补丁文件路径 |
| patches.{filename}.patch_description | 条件必填 | string | 补丁描述 |
| patches.{filename}.patch_type | 条件必填 | string | portability / bugfix / backport |

## 5. 命名规范

### 目录名
- 软件目录：`{首字母}/{软件名}/`，如 `c/cmake/`
- 版本目录：`{version}/`，如 `3.30.0/`
- 软件名使用小写

### 文件名
- 补丁：`{4位序号}-{简短描述}.patch`
- Conan 包引用：`{name}/{version}`

## 6. 与 CI 的关系

```
archives/{l}/{name}/
  ├── commands.json    ← CI: 工具类型包必须有（L0k 校验）
  └── {ver}/
    ├── conanfile.py     ← CI: conan create 读取此文件构建
    ├── conandata.yml    ← CI: conan create 读取源码地址和补丁
    ├── test_package/    ← CI: conan create 自动执行 L1 测试
    ├── manifest.yaml    ← CI: 不读取（仅人类交叉校验）
    ├── notes.md         ← CI: 不读取（仅人类参考）
    ├── patches/         ← CI: conandata.yml 引用，apply_conandata_patches 应用
    └── reports/         ← CI: conan_verify 写入验证报告
```

CI 流水线（ci/ 目录脚本）：
1. `ci/conan/setup.sh` — 初始化 Conan 环境 + profile + remote
2. `ci/conan/build_and_test.sh` — 扫描 archives/ → `conan create` 每个包 → 五级测试
3. `ci/conan/upload.sh` — `conan upload` 到 CNB 制品仓（仅 release）
4. `ci/artifacts/sign.sh` — GPG 签名（非阻塞）

## 7. 旧版本迁移（v2.0 → v3.0）

> 迁移工具：`ohc-run.py conan-migrate <软件名> <版本>`（待实现）
> 迁移暂缓，先完成基础架构。

| v2.0 文件 | v3.0 处置 | 说明 |
|-----------|-----------|------|
| `manifest.yaml` | 保留 | 降级为交叉校验，新增 conan_ref 字段 |
| `notes.md` | 保留 | 不变 |
| `patches/` | 保留 | 需在 conandata.yml 中声明 |
| `packaging/` | 删除 | Conan 体系替代 |
| (无 conanfile.py) | 新增 | 从 manifest.yaml + notes.md 生成 |
| (无 conandata.yml) | 新增 | 从 manifest.yaml source 段生成 |
| (无 test_package/) | 新增 | 从模板生成基础测试 |
