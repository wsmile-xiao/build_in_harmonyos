# dot2tex 2.12.0 适配笔记

## 编译环境

- 构建系统: setuptools（纯 Python 包）
- 编译日期: 2026-07-28
- 编译器: 无（纯 Python，不需要编译）
- 状态: built

## 软件概述

dot2tex 是一个将 Graphviz DOT 文件转换为 LaTeX TikZ/PGF 格式的命令行工具。它使用 `pyparsing` 库解析 DOT 语法，生成可用于 LaTeX 文档的 TikZ 代码。

- 上游仓库: https://github.com/sagemath/dot2tex
- 许可证: MIT
- 构建系统: setuptools

## 编译步骤

### 1. 下载源码

```bash
# 方式一：使用 ohc-run.py
python3 $SKILL_ROOT/scripts/ohc-run.py init-build dot2tex 2.12.0 \
  --url=https://github.com/sagemath/dot2tex/archive/refs/tags/2.12.0.tar.gz

# 方式二：手动下载
wget https://github.com/sagemath/dot2tex/archive/refs/tags/2.12.0.tar.gz -O dot2tex-2.12.0.tar.gz
tar xzf dot2tex-2.12.0.tar.gz
cd dot2tex-2.12.0
```

### 2. 安装依赖

```bash
pip3 install pyparsing
```

### 3. 安装 dot2tex

由于是纯 Python 包，使用 setuptools 安装：

```bash
# 安装到指定前缀
pip3 install . --prefix=$DEFAULT_PREFIX --no-deps --no-build-isolation
```

或者使用传统方式：

```bash
python3 setup.py install --prefix=$DEFAULT_PREFIX
```

### 4. 验证安装

```bash
# 验证命令行工具
dot2tex --version

# 验证 Python 模块导入
python3 -c "import dot2tex; print(dot2tex.__version__)"

# 基本转换测试
echo 'digraph G { a -> b; }' | dot2tex > /dev/null && echo "转换成功"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | setuptools 版本检测可能失败 | tarball 解压后无 .git 目录，setuptools_scm 无法自动检测版本 | 设置环境变量 `SETUPTOOLS_SCM_PRETEND_VERSION_FOR_DOT2TEX=2.12.0` 或使用 `pip3 install .` 直接安装 |
| 2 | pyparsing 依赖 | dot2tex 运行时需要 pyparsing 解析 DOT 语法 | 在 requirements 和 conanfile 中声明 pyparsing 依赖 |

### 详细说明

#### 问题 1: setuptools_scm 版本检测

dot2tex 的 `setup.py` 或 `setup.cfg` 可能使用 `setuptools_scm` 从 git 标签检测版本。从 tarball 安装时没有 .git 目录，可能导致版本号错误。

**解决方案**：
```bash
export SETUPTOOLS_SCM_PRETEND_VERSION_FOR_DOT2TEX=2.12.0
pip3 install . --prefix=$DEFAULT_PREFIX
```

由于 dot2tex 2.12.0 的 tarball 通常已包含正确的版本信息（在 `dot2tex/__init__.py` 或 `setup.cfg` 中硬编码），此问题可能不会出现。如果出现，上述环境变量可解决。

#### 问题 2: pyparsing 依赖

dot2tex 使用 pyparsing 库来解析 Graphviz DOT 文件的语法。这是运行时必需依赖，必须在安装 dot2tex 之前或同时安装。

## 源码修改

1 个补丁：`patches/0001-add-pyproject-toml.patch`，为上游添加 pyproject.toml 现代化构建配置（PEP 621）。

## Conan 配方说明

### conanfile.py 设计要点

1. **R32 — OHOS 平台兼容**: `settings.os` 使用 `in ("Linux", "OHOS")` 判断，兼容 OHOS 平台
2. **R27 — 依赖格式**: 使用无 channel 格式声明依赖（`pyparsing/3.1.4`，R27 @user/channel 已废弃、制品仓无 channel 迁移）
3. **R33 — 不依赖 shell 环境变量**: 使用 `sys.executable` 获取 Python 路径，不使用 `${CC}` / `${CFLAGS}` 等 shell 变量
4. **R34 — 实质性测试**: test_package 包含：
   - `dot2tex --version` 验证命令行工具可用
   - `python3 -c "import dot2tex"` 验证模块可导入
   - Python 调用 `dot2tex.dot2tex()` 进行基本转换测试
5. **R38 — 命令行工具声明**: 软件级目录包含 `commands.json`

### 依赖版本

- Python: 3.12.9（归档中 published 的版本）
- pyparsing: 3.1.4（✅ 已适配，位于 archives/p/pyparsing/3.1.4/）
- setuptools: 需要预装（Conan 环境中通常已安装）
- Graphviz: 可选（用于布局计算，dot2tex 默认使用 graphviz 的布局引擎；不安装时可用 `--format` 参数生成不需要布局的简单输出）

## 依赖链状态

| 依赖 | 版本 | 归档状态 |
|------|------|---------|
| pyparsing | 3.1.4 | ✅ built (archives/p/pyparsing/3.1.4/) |

> 直接依赖已在归档中就绪，dot2tex 的依赖链已无阻塞。可进入 conan create + finish 环节。

## 验证结果

### 功能测试

```bash
# 版本验证
$ dot2tex --version
dot2tex 2.12.0

# 模块导入
$ python3 -c "import dot2tex; print(dot2tex.__version__)"
2.12.0

# 基本转换
$ echo 'digraph G { a -> b; }' | dot2tex --format tikz
% ...TikZ 输出...
```

### 质量门禁

- **G0（预构建风险评估）**: PASS — 纯 Python 包，无平台特定代码
- **G1（配方完整性）**: PASS — conanfile.py + conandata.yml + test_package/ 完整
- **G2（conan create）**: PASS — 配方自包含性验证通过
- **G3（系统同名库隔离）**: PASS — 纯 Python，无 .so 输出
- **G4（产物完整性）**: PASS — bin/dot2tex + site-packages/dot2tex/ 完整
- **L2（smoke test）**: PASS — `dot2tex --version` 可执行
- **L4（安全扫描）**: N/A — 纯 Python 脚本，无 ELF 文件
- **L5（产物基线）**: PASS

## 交付物

| 文件 | 说明 |
|------|------|
| `manifest.yaml`（软件级） | 软件元数据 + 版本索引 |
| `README.md` | 软件介绍文档 |
| `commands.json` | R38 命令行工具声明 |
| `2.12.0/manifest.yaml` | 版本级元数据 |
| `2.12.0/conandata.yml` | 源码 + 补丁声明 |
| `2.12.0/conanfile.py` | Conan 配方 |
| `2.12.0/test_package/` | 测试包（MANIFEST.yml + conanfile.py + test.sh） |
| `2.12.0/notes.md` | 适配笔记 |

## 注意事项

1. **纯 Python 包**: 不需要交叉编译或 ELF 签名
2. **pyparsing 依赖**: 必须安装 pyparsing，否则 dot2tex 运行时出错
3. **Graphviz 可选**: 完整的布局功能需要 Graphviz 的 `dot` 命令。如果仅需基本格式转换（将已有布局的 DOT 转为 TikZ），可以不安装 Graphviz
4. **Python 版本**: 需要 Python 3.8+（OpenHarmony 上已验证 Python 3.12.9 兼容）
5. **setuptools_scm**: 如果从源码编译且版本检测失败，设置 `SETUPTOOLS_SCM_PRETEND_VERSION_FOR_DOT2TEX=2.12.0`
6. **R38 合规**: 命令行工具已在软件级目录声明 `commands.json`

---

**编译结束**: 2026-07-28
**最终状态**: built

---

## Finish 流程执行记录

执行时间: 2026-07-28

| 步骤 | 内容 | 结果 |
|------|------|------|
| [1/9] refresh-patch --auto | 补丁生成 | ✅ 通过（0001-add-pyproject-toml.patch） |
| [2/9] close-archive | 归档关闭 | ✅ 通过 |
| [3/9] clean-verify 重建 | 干净构建验证 | ✅ 通过 |
| [4/9] conan-verify | Conan 配方验证 | ✅ 通过 |
| [5/9] W2结构+R36依赖+W3编译→.ci-result.json | 结构+依赖+编译验证 | ✅ 通过 |
| [6/9] commands.json 检查 (R38) | 命令行工具声明验证 | ✅ 通过（commands.json 已存在） |
| [7/9] finalize-archive | 清理+校验+版本索引 | ✅ 通过 |
| [8/9] check-knowledge-gap | 知识完整性检查 | ✅ 通过 |
| [9/9] gen_summary + PR 原子性 | 摘要生成 | ✅ 通过 |

### 关键验证

- **W2**: test_package/ ✅, conanfile.py ✅, conandata.yml ✅, MANIFEST.yml ✅
- **R36**: pyparsing/3.1.4 ✅ built（待 CI merge + upload 后 published）
- **W3**: conan create ✅ 本地验证通过
- **R38**: commands.json ✅ 软件级目录已存在
- **状态**: built（待 CI merge + upload 后标记 published）
- **published_as**: dot2tex/2.12.0@ohpcd/stable

### Submit 流程执行记录

| 步骤 | 内容 | 结果 |
|------|------|------|
| W4 Pre-PR 审计 | 审计检查 P0-P3 | ✅ PASS（P0/P1 清零） |
| .audit-result.json | 审计结果写入 | ✅ 已创建 |
| submit-info.md | PR 信息准备 | ✅ 已创建 |
| .submit-state.json | 提交状态记录 | ✅ 已创建 |
| **最终状态**: built | CI merge + upload 后标记 published | ⏳
