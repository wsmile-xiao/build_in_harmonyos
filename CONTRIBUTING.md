# 贡献指南

感谢您对 OpenHarmony 编译智能体项目的关注！本文档将帮助您了解如何为项目贡献新的软件编译档案。

## 目录

- [如何添加新软件档案](#如何添加新软件档案)
- [补丁命名规范](#补丁命名规范)
- [manifest.yaml 必填字段](#manifestyaml-必填字段)
- [测试报告要求](#测试报告要求)
- [PR 提交流程](#pr-提交流程)

---

## 如何添加新软件档案

### 1. 创建目录结构

软件档案按照首字母组织，目录结构如下：

```
archives/{首字母}/{软件名}/{版本}/
├── manifest.yaml        # 元数据清单（必须）
├── README.md            # 编译说明（必须）
├── patches/             # 补丁目录
│   ├── 0001-xxx.patch
│   └── 0002-xxx.patch
├── reports/             # 报告目录
│   ├── build-report.md  # 编译过程记录
│   ├── test-report.md   # 测试报告
│   └── compatibility.md # 兼容性评估
├── scripts/             # 编译脚本（可选）
│   └── build.sh
└── logs/                # 完整日志（可选）
    └── build.log
```

### 2. 创建档案步骤

#### 步骤 1: 创建目录

```bash
# 示例：添加 curl 7.88.1
mkdir -p archives/c/curl/7.88.1/{patches,reports,scripts,logs,tests}
```

#### 步骤 2: 使用模板创建文件

```bash
# 复制模板
cp templates/manifest.yaml archives/c/curl/7.88.1/
cp templates/README.md archives/c/curl/7.88.1/
cp templates/build-report.md archives/c/curl/7.88.1/reports/
cp templates/test-report.md archives/c/curl/7.88.1/reports/
```

#### 步骤 3: 填写 manifest.yaml

编辑 `manifest.yaml`，填写软件信息（详见下文必填字段说明）。

#### 步骤 4: 生成补丁文件

如果您对源码进行了修改，生成补丁文件：

```bash
# 在源码目录下
diff -Naur original_source/ modified_source/ > 0001-description.patch

# 或使用 git
git diff > 0001-description.patch
```

#### 步骤 5: 更新索引

编辑 `archives/_index.yaml`，添加新软件的索引信息：

```yaml
software_index:
  # ...
  curl:
    versions: ["7.88.1"]
    build_system: autotools
    status: success
    path: archives/c/curl
```

### 3. 使用辅助脚本

我们提供了辅助脚本来简化流程：

```bash
# 自动创建档案目录结构
./scripts/create-archive.sh <软件名> <版本>

# 检测构建系统类型
./scripts/detect-build-system.sh <源码目录>

# 验证补丁文件
./scripts/validate-patch.sh <补丁文件> <源码目录>
```

---

## 补丁命名规范

### 命名格式

补丁文件必须遵循以下命名格式：

```
NNNN-description.patch
```

- **NNNN**: 四位数字序号（0001-9999）
- **description**: 简短描述，使用小写字母和连字符

### 示例

```
patches/
├── 0001-add-harmonyos-support.patch
├── 0002-fix-configure-ac.patch
├── 0003-update-config-guess.patch
└── 0004-fix-musl-compat.patch
```

### 命名最佳实践

1. **序号连续**: 从 0001 开始连续编号
2. **描述清晰**: 补丁用途一目了然
3. **单一职责**: 每个补丁解决一个问题
4. **避免空格**: 使用连字符代替空格

### 补丁文件要求

1. **格式标准**: 使用 unified diff 格式
2. **包含上下文**: 至少保留 3 行上下文
3. **添加说明**: 在补丁文件开头添加注释说明用途

示例：

```diff
From: Your Name <your.email@example.com>
Date: Mon, 1 Jan 2024 00:00:00 +0000
Subject: [PATCH] Add HarmonyOS platform support

This patch adds configuration support for HarmonyOS platform
by updating config.guess and config.sub scripts.

diff --git a/config.guess b/config.guess
--- a/config.guess
+++ b/config.guess
@@ -1,4 +1,4 @@
-#!/bin/sh
+#!/bin/bash
 # Attempt to guess a canonical system name.
```

---

## manifest.yaml 必填字段

### 核心必须字段

以下字段是**必须填写**的：

```yaml
# 软件名称（小写）
software: example

# 版本号
version: 1.0.0

# 编译状态
# - success: 编译成功，测试通过
# - partial: 编译成功，部分功能异常
# - failed: 编译失败
status: success

# 构建系统类型
# - autotools: configure + make
# - cmake: CMakeLists.txt
# - custom-perl: 自定义 Perl Configure（如 OpenSSL）
# - meson: meson.build
# - makefile: 直接 Makefile
# - qmake: .pro 文件
build_system: autotools

# 编译日期（YYYY-MM-DD）
compile_date: 2024-01-01
```

### 推荐填写字段

以下字段建议填写以提供完整信息：

```yaml
# 依赖信息
dependencies:
  required: []      # 必需依赖
  optional: []      # 可选依赖
  recommended: []   # 推荐依赖

# 编译配置
build_config:
  target: aarch64-unknown-linux-ohos
  configure_options: []
  cflags: ""
  ldflags: ""

# 补丁信息
patches_applied:
  - file: 0001-xxx.patch
    purpose: 补丁用途说明
    lines_changed: 50

# 兼容性评估
compatibility:
  level: high       # high | medium | low
  issues: []
  notes: ""

# 测试结果
test_results:
  type: official     # official | manual | skipped
  total: 0
  passed: 0
  failed: 0
  note: ""

# 知识沉淀
knowledge_gained: []

# 参考链接
references: []
```

### 完整模板

完整的 `manifest.yaml` 模板位于 `templates/manifest.yaml`。

---

## 测试报告要求

### 测试类型

1. **official**: 使用官方测试套件
2. **manual**: 手动功能测试
3. **skipped**: 跳过测试（需说明原因）

### 测试报告内容

在 `reports/test-report.md` 中应包含：

#### 1. 基本信息

- 软件名称和版本
- 测试日期
- 测试环境（系统版本、编译器版本等）
- 测试类型

#### 2. 测试执行

##### 测试命令
```bash
make test
# 或
python -m pytest
```

##### 测试结果
- 总测试数: 100
- 通过: 95
- 失败: 3
- 跳过: 2

#### 3. 失败分析

对于失败的测试，需要：

- 列出失败的测试用例
- 分析失败原因（系统限制、平台差异等）
- 评估对核心功能的影响

#### 4. 关键功能验证

列出验证过的关键功能：

```markdown
## 关键功能验证

| 功能 | 状态 | 说明 |
|------|------|------|
| 基本操作 | ✓ | 正常工作 |
| 网络通信 | ✓ | SSL/TLS 正常 |
| 文件操作 | ✗ | 权限问题 |
```

### 兼容性评估

在 `reports/compatibility.md` 中记录：

1. **兼容性等级**：high / medium / low
2. **可用功能列表**
3. **限制和注意事项**
4. **系统调用兼容性**

---

## PR 提交流程

### 1. Fork 和克隆

```bash
# Fork 仓库后克隆
git clone https://github.com/YOUR_USERNAME/build_in_harmonyos.git
cd build_in_harmonyos

# 添加上游仓库
git remote add upstream https://github.com/ORIGINAL_REPO/build_in_harmonyos.git
```

### 2. 创建分支

```bash
# 创建新分支
git checkout -b add-software-curl
```

### 3. 添加新软件档案

按照上述流程创建新的软件档案。

### 4. 验证更改

```bash
# 验证目录结构
find archives/c/curl -type f

# 验证 manifest.yaml 格式
python -c "import yaml; yaml.safe_load(open('archives/c/curl/7.88.1/manifest.yaml'))"

# 验证补丁文件
./scripts/validate-patch.sh archives/c/curl/7.88.1/patches/*.patch

# 测试补丁应用
cd /path/to/source
patch --dry-run -p1 < /path/to/archives/c/curl/7.88.1/patches/0001-xxx.patch
```

### 5. 提交更改

```bash
# 添加文件
git add archives/c/curl/7.88.1/
git add archives/_index.yaml

# 提交
git commit -m "Add curl 7.88.1 archive with HarmonyOS support

- Add build configuration for HarmonyOS
- Fix configure script for platform detection
- Tested with manual test suite

Closes #XXX"
```

### 6. 推送并创建 PR

```bash
# 推送到您的 fork
git push origin add-software-curl

# 在 GitHub 上创建 Pull Request
```

### 7. PR 检查清单

在提交 PR 前，请确保：

- [ ] 目录结构正确（`archives/{首字母}/{软件名}/{版本}/`）
- [ ] `manifest.yaml` 包含所有必填字段
- [ ] 补丁文件命名符合规范（`NNNN-description.patch`）
- [ ] 补丁可以正确应用到源码
- [ ] 更新了 `archives/_index.yaml` 索引
- [ ] 提供了测试报告
- [ ] README.md 包含编译说明
- [ ] 代码审查后及时响应反馈

### 8. 代码审查

PR 提交后会进行代码审查，关注点包括：

1. **档案结构完整性**
2. **补丁质量和可维护性**
3. **manifest.yaml 信息准确性**
4. **测试覆盖充分性**
5. **文档清晰度**

### 9. 合并标准

PR 将在以下条件满足后合并：

- 通过所有自动检查
- 至少一位维护者审查通过
- 解决所有讨论的问题
- 符合项目代码规范

---

## 需要帮助？

如果您在贡献过程中遇到问题：

1. 查看 `knowledge/` 目录下的知识库文档
2. 参考 `archives/` 下已有的软件档案示例
3. 在 GitHub Issues 中提问
4. 联系项目维护者

感谢您的贡献！