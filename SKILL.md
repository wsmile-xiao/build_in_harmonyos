---
# 固定元数据头（必须，AI 优先读取）
name: openharmony-compile-agent
description: 鸿蒙系统编译智能体，提供软件编译的完整流程指导、知识库检索和档案管理
version: 2.0.0
author: OpenHarmony Community
permissions: 文件读写权限、Shell执行权限、网络访问权限（可选，用于下载源码）
---

# OpenHarmony 编译智能体 SKILL

## 1. Description

本技能是一个**智能编译助手**，帮助 AI 高效完成鸿蒙系统上的软件编译任务。核心能力：

1. **编译执行指导**：标准化的编译流程和问题排查
2. **知识库检索**：快速定位历史经验和解决方案
3. **档案管理**：结构化存储补丁、报告和元数据
4. **质量保证**：验证编译结果和兼容性评估

### 核心设计理念

```
知识不遗漏 → 档案结构化 → 检索高效化 → 复用精准化
```

### ⚠️ 强制规范

> **软链接处理**：鸿蒙系统的 SELinux 策略限制软链接。在编译、安装、验证的各个阶段，**必须验证软链接是否可执行**，不能仅检查是否存在。详细规范见 `knowledge/environment.md` 第 9 节。

> **代码来源**：所有源码**必须从官方一手源下载**，不得使用第三方镜像或非官方源。这确保代码与常规理解的功能匹配，避免安全风险。下载前需确认官方发布地址。

> **官方测试**：执行官方测试套件（如 `make check`）是**强制要求**，不是可选项。必须运行测试并记录结果，即使测试因环境限制失败也需明确记录原因。

> **核心功能验证**：编译后**必须验证核心功能**，不能只测试 `--version`。例如：
> - htop：必须测试进程显示、F键功能
> - strace：必须测试实际系统调用追踪
> - rsync：必须测试文件同步功能
> 核心功能异常必须在档案中记录原因和解决方案。

> **依赖软件独立归档**：编译目标软件时，如果需要先编译安装依赖库（如 libpipeline 之于 man-db），这些依赖软件**必须作为独立项目单独创建归档**（manifest.yaml + README.md），不能仅作为主软件归档的一个章节。每个依赖库有自己的版本生命周期和补丁记录，独立归档有助于未来复用和跨项目引用。

> **打包验证完整性**：制作可移植包时，**必须对所有 ELF 文件（包括 lib-dynload/ 下的扩展模块）设置 RPATH 并重新签名**。不能仅处理主程序和主共享库而遗漏扩展模块。详见 `knowledge/packaging.md` §5.4 和 `knowledge/error-patterns.md` E042。

> **Shell 脚本 POSIX 兼容**：为鸿蒙编写的所有 shell 脚本**必须使用 POSIX 兼容语法**（`#!/bin/sh` + toybox ash 兼容），不能依赖 `${BASH_SOURCE}`、`[[ ]]`、数组等 bash 特性。详见 `knowledge/harmonyos-specifics.md` §3 和 `knowledge/packaging.md` §5。

## 2. When to use

- 用户说："帮我在鸿蒙电脑上编译 XXX"
- 用户说："XX 软件在鸿蒙上编译失败，如何解决"
- 用户说："查询 XX 软件的编译历史"
- 用户说："生成 XX 软件的兼容性报告"
- 用户说："鸿蒙系统用什么编译器？"
- 用户说："如何在鸿蒙系统上配置 autotools？"

## 3. How to use

### 3.1 编译任务执行流程

当用户请求编译软件时，按以下阶段执行：

#### Phase 1: 检索历史知识（必须先执行）

```
检索路径：
1. archives/{首字母}/{软件名}/{版本}/manifest.yaml
   → 精确匹配：直接复用补丁和脚本
   
2. archives/{首字母}/{软件名}/*/manifest.yaml
   → 相似版本：评估补丁可复用性
   
3. knowledge/build-systems.md
   → 构建系统知识：适配策略
```

**检索命令示例**：
```bash
# 检查是否有现成档案
ls archives/o/openssl/*/manifest.yaml

# 查看档案内容
cat archives/o/openssl/1.1.1w/manifest.yaml
```

#### Phase 2: 环境准备

1. **检查环境变量（必须）**
   ```bash
   # 必须检查的环境变量
   echo "TMPDIR: ${TMPDIR:?未设置}"
   echo "CC: ${CC:?未设置}"
   echo "CFLAGS: ${CFLAGS:?未设置}"
   echo "DEFAULT_PREFIX: ${DEFAULT_PREFIX:?未设置}"
   ```
   详细配置参考 `knowledge/environment.md` 第 4 节

2. **检查依赖工具（必须验证软链接可用性）**
   ```bash
   # ⚠️ 强制规范：必须验证软链接是否真正可用
   # 鸿蒙系统软链接可能存在但无法执行（SELinux 限制）
   
   # 重要：ln -sf 在鸿蒙上会创建带随机后缀的文件！
   # 必须使用 rm -f + ln -s 的方式
   
   check_symlink() {
       local link=$1
       local expected=$2
       
       # 1. 检查文件是否存在
       if [ ! -e "$link" ]; then
           echo "❌ $link 不存在"
           return 1
       fi
       
       # 2. 检查是否为软链接
       if [ -L "$link" ]; then
           # 3. 验证软链接是否可执行
           if "$link" --version >/dev/null 2>&1; then
               echo "✅ $link 软链接可用"
               return 0
           else
               echo "❌ $link 软链接存在但无法执行，需要使用规避方式"
               return 1
           fi
       fi
       
       # 4. 普通文件，检查是否可执行
       if [ -x "$link" ]; then
           echo "✅ $link 可执行"
           return 0
       fi
       
       return 1
   }
   
   # 创建软链接的正确方式
   create_symlink() {
       local target=$1
       local link=$2
       
       # 关键：先删除再创建，不能用 ln -sf
       rm -f "$link"
       ln -s "$target" "$link"
   }
   
   # 检查关键工具
   check_symlink "$HOME/usr/local/bin/cc" "clang" || create_wrapper "cc" "/data/service/hnp/bin/clang"
   ```

3. **软链接规避方式（强制使用）**
   ```bash
   # 当软链接不可用时，使用 wrapper 脚本（推荐）
   create_wrapper() {
       local name=$1
       local target=$2
       cat > "$HOME/usr/local/bin/$name" << EOF
   #!/bin/sh
   exec $target "\$@"
   EOF
       chmod +x "$HOME/usr/local/bin/$name"
   }
   ```

4. 准备编译目录结构

#### Phase 3: 编译执行

1. 识别构建系统类型（参考 `knowledge/build-systems.md`）
2. 应用补丁（如有历史档案）
3. 执行编译命令
4. **执行 make install 时检查软链接（必须）**
   ```bash
   # ⚠️ 强制规范：make install 后必须验证安装产物
   # 很多软件的 make install 会创建软链接，需要验证
   
   make install
   
   # 检查安装的可执行文件是否可用
   for bin in $DEFAULT_PREFIX/bin/*; do
       if [ -L "$bin" ]; then
           if ! "$bin" --version >/dev/null 2>&1; then
               echo "⚠️ $bin 软链接不可用，创建 wrapper 脚本"
               target=$(readlink "$bin")
               rm -f "$bin"
               cat > "$bin" << EOF
   #!/bin/sh
   exec $target "\$@"
   EOF
               chmod +x "$bin"
           fi
       fi
   done
   ```
5. 记录编译过程

#### Phase 4: 验证与归档

1. **验证编译产物（必须检查软链接可用性）**
   ```bash
   # ⚠️ 强制规范：验证阶段必须检查所有产物软链接
   # 不能仅检查文件是否存在，必须验证可执行性
   
   verify_installation() {
       local bin=$1
       
       # 1. 检查文件存在
       [ -e "$bin" ] || { echo "❌ $bin 不存在"; return 1; }
       
       # 2. 验证可执行性
       "$bin" --version >/dev/null 2>&1 || {
           echo "❌ $bin 无法执行"
           return 1
       }
       
       echo "✅ $bin 验证通过"
       return 0
   }
   ```
2. **执行官方测试套件（必须）**
   - 运行 `make check` 或 `make test`
   - 记录测试结果（通过/失败/跳过）
   - 分析失败原因：编译问题 vs 环境兼容性问题
   - 创建测试报告 `reports/test-report.md`
   - 如果测试失败，必须在 manifest.yaml 中说明原因
3. **补丁完整性校验（必须，在生成补丁之前执行）**
   ```bash
   # ⚠️ 强制规范：生成补丁前必须与原始源码做 diff 比对，
   # 确保所有源码修改都被捕获为补丁文件，防止遗漏。
   # 不能仅凭对话记录"回忆"做过哪些修改。
   
   # 1. 从原始 tarball 解压到临时目录
   mkdir -p /tmp/patch_verify
   cd /tmp/patch_verify
   tar xf /path/to/original.tar.xz <软件名>-<版本>/ 2>/dev/null
   
   # 2. 对比修改后的源码与原始源码
   diff -ruN \
       <软件名>-<版本>/ \
       /path/to/modified-source/ \
       > /tmp/patch_verify/all_changes.diff
   
   # 3. 检查 diff 结果
   # - 如果无差异 → 没有源码修改，跳过
   # - 如果有差异 → 逐个检查差异，确认每个修改都已（或将被）生成为补丁文件
   # - 排除 build 目录、.o 文件、Makefile 等构建产物
   ```
   **校验要点**：
   - 对话中讨论的补丁数量必须与 diff 结果一致
   - diff 中的每个文件修改都必须有对应的补丁文件
   - 如果发现遗漏的修改，必须补充生成补丁
   - **典型案例**：编译过程中为修复编译错误临时修改的源文件（如添加 `__attribute__((unused))`），容易在归档时被遗漏
   
   > **教训**：strace 6.19 编译时修改了 `src/sigreturn.c` 抑制 clang 的 `-Wunused-function` 警告，但归档时仅生成了 config.guess 和 config.sub 的补丁，遗漏了源码修改。若当时执行此 diff 校验步骤，即可避免。

4. 创建软件档案：
   - 生成补丁文件（基于上一步的校验结果）
   - 验证每个补丁可干净应用：`patch --dry-run -p1 < patches/NNNN-xxx.patch`
   - 创建 manifest.yaml
   - 编写 README.md
   - 记录测试报告

5. **编译复盘与知识库更新（必须，Phase 4 最后一步）**
   > **⚠️ 强制规范**：每次编译完成后，必须回顾本次编译过程中遇到的所有问题和解决方案，
   > 识别出尚未被知识库收录的新模式，及时更新知识库文件。
   > 知识库是跨会话积累的核心资产，不能只积累档案而忽视知识沉淀。

   **复盘步骤**：

   1. **提取本次编译的新经验**
      ```
      回顾清单：
      - 编译过程中遇到了哪些 configure/编译/链接/运行时错误？
      - 解决方案是什么？是否具有通用性（其他软件可能也会遇到）？
      - manifest.yaml 中的 knowledge_gained 条目是否都是新的？
      - 是否发现了新的鸿蒙系统限制或兼容性问题？
      ```

   2. **比对现有知识库，识别遗漏**
      ```bash
      # 检查 error-patterns.md 是否已覆盖本次遇到的错误
      grep "错误关键词" knowledge/error-patterns.md

      # 检查 troubleshooting.md 是否已覆盖
      grep "问题描述" knowledge/troubleshooting.md
      ```

   3. **按类型归档到对应知识库文件**
      ```
      | 遇到的问题类型 | 应更新的文件 |
      |---------------|-------------|
      | 新的编译/链接/运行时错误模式 | knowledge/error-patterns.md（新增 Exxx） |
      | 排查思路和诊断流程 | knowledge/troubleshooting.md |
      | musl 与 glibc 的差异 | knowledge/musl-compat.md |
      | 构建系统特殊处理方式 | knowledge/build-systems.md |
      | 鸿蒙系统环境特性/限制 | knowledge/environment.md |
      | 编译依赖关系/顺序 | knowledge/dependencies.md |
      ```

   4. **更新知识库**
      - 为新模式分配编号（error-patterns.md 的 E0xx 序号递增）
      - 补充错误特征、根因分析、验证命令、解决方案
      - 更新相关索引表

   **判断标准**——以下情况**必须**写入知识库：
   - ✅ 同类问题可能在未来编译其他软件时复现
   - ✅ 解决方案具有通用性，不局限于当前软件
   - ✅ 揭示了鸿蒙系统与 Linux 的差异
   - ✅ 编译选项是鸿蒙特有的（如 `--disable-mpers`、`--without-shared`）

   **以下情况**可以**不**写入：
   - ❌ 仅当前软件特有的逻辑 bug
   - ❌ 上游已知且已修复的问题
   - ❌ 一次性环境问题（如磁盘空间不足）

   > **教训**：strace 6.19 编译遗漏了 `src/sigreturn.c` 的补丁，原因是没有在归档前做 diff 校验；
   > 同时 clang 的 `-Wunused-function` 对 static inline 函数的严格行为也没有被记录为通用知识。
   > 如果每次编译后都执行复盘，这两个问题本可以在第一时间被发现和沉淀。

### 3.2 知识检索策略

| 检索场景 | 检索路径 | 用途 |
|----------|----------|------|
| 精确软件版本 | `archives/{letter}/{name}/{version}/` | 复用完整方案 |
| 相似版本 | `archives/{letter}/{name}/` | 评估补丁兼容性 |
| 构建系统知识 | `knowledge/build-systems.md` | 适配策略 |
| 环境配置 | `knowledge/environment.md` | 系统特性 |
| 鸿蒙特有机制 | `knowledge/harmonyos-specifics.md` | 签名、SELinux 等 |
| 可移植打包 | `knowledge/packaging.md` | RPATH、strip、签名流程 |
| Python 扩展编译 | `knowledge/python-extensions.md` | musl BIND_NOW、静态链接、扩展模块 |
| ptrace 替代方案 | `knowledge/ptrace-alternatives.md` | LD_PRELOAD、strace 替代 |
| 常见问题 | `knowledge/troubleshooting.md` | 问题排查 |
| 错误模式 | `knowledge/error-patterns.md` | 解决方案 |

### 3.3 软件档案结构

每个成功编译的软件应创建标准化档案：

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

### 3.4 manifest.yaml 规范

```yaml
# 必须字段
software: openssl          # 软件名
version: 1.1.1w           # 版本号
status: success           # success | partial | failed
build_system: custom-perl # autotools | cmake | custom-perl | meson | makefile
compile_date: 2024-03-22  # 编译日期

# 依赖信息
dependencies:
  required: [perl]        # 必需依赖
  optional: [zlib]        # 可选依赖

# 编译配置
build_config:
  target: linux-aarch64-ohos
  options:
    - --prefix=$HOME/usr/local
    - no-asm

# 补丁信息
patches_applied:
  - file: 0001-support-build-in-harmonyos.patch
    purpose: 添加 HarmonyOS 平台配置
    lines_changed: 120

# 兼容性评估
compatibility:
  level: high             # high | medium | low
  issues: []              # 已知问题
  notes: "核心功能正常"

# 测试结果
test_results:
  type: manual            # official | manual | skipped
  passed: 29
  failed: 6
  note: "核心加密功能正常"

# 知识沉淀
knowledge_gained:
  - "使用 no-asm 禁用汇编优化避免 BAD_SIGNATURE"
  - "Python _ssl 模块需要手动链接 libssl"

# 参考
references:
  - https://www.openssl.org/docs/
```

## 4. Directory Structure

```
openharmony-compile-agent/
├── SKILL.md                    # 本文档
├── MISSING_TOOLS.md            # 缺失工具清单
├── README.md                   # 项目说明
│
├── knowledge/                  # 静态知识库
│   ├── build-systems.md        # 构建系统知识
│   ├── dependencies.md         # 编译依赖顺序与推荐顺序
│   ├── environment.md          # 鸿蒙环境特性
│   ├── harmonyos-specifics.md  # 鸿蒙特有机制（签名、SELinux 等）
│   ├── packaging.md            # 可移植打包指南
│   ├── troubleshooting.md      # 问题排查指南
│   ├── error-patterns.md       # 错误模式库
│   └── musl-compat.md          # musl 兼容性
│
├── templates/                  # 模板文件
│   ├── manifest.yaml           # manifest 模板
│   ├── README.md               # README 模板
│   ├── build-report.md         # 编译报告模板
│   └── test-report.md          # 测试报告模板
│
├── scripts/                    # 辅助脚本
│   ├── detect-build-system.sh  # 构建系统检测
│   ├── create-archive.sh       # 创建档案
│   └── validate-patch.sh       # 验证补丁
│
├── archives/                   # 软件编译档案
│   ├── a/                      # 按首字母组织
│   │   └── automake/
│   │       └── 1.16.5/
│   ├── b/
│   │   ├── bash/
│   │   │   └── 5.3/
│   │   └── bzip2/
│   │       └── 1.0.8/
│   ├── ...
│   └── _index.yaml             # 软件索引（快速查找）
│
└── .opendesk/                  # SKILL 元数据
    └── memory/                 # 记忆存储
```

## 5. Tools

本 SKILL 建议使用以下工具（通过 terminal 工具调用）：

### 5.1 档案检索

```bash
# 检索软件档案
find archives -name "manifest.yaml" | xargs grep -l "software: openssl"

# 快速查看索引
cat archives/_index.yaml
```

### 5.2 创建档案

```bash
# 使用模板创建新档案
cp templates/manifest.yaml archives/o/openssl/1.1.1w/
cp templates/README.md archives/o/openssl/1.1.1w/
```

### 5.3 验证补丁

```bash
# 验证补丁是否正确
patch --dry-run -p1 < archives/o/openssl/1.1.1w/patches/0001-xxx.patch
```

## 6. Notes

### 6.1 知识拆分原则

原有 SKILL.md 内容过大，已拆分为多个知识文件：

| 原位置 | 新位置 |
|--------|--------|
| 构建系统知识 | `knowledge/build-systems.md` |
| 编译依赖顺序 | `knowledge/dependencies.md` |
| 环境检查 | `knowledge/environment.md` |
| 文件系统架构分析 | `knowledge/filesystem-analysis.md` |
| 常见问题 | `knowledge/troubleshooting.md` |
| musl 兼容性 | `knowledge/musl-compat.md` |
| 问题案例 | `knowledge/error-patterns.md` |
| musl/glibc 接口对比 (ISO C + POSIX) | `knowledge/musl-glibc-full-comparison-iso-posix.md` |
| musl/glibc 接口对比 (GNU + Linux) | `knowledge/musl-glibc-full-comparison-gnu-linux.md` |
| musl/glibc 差异对开发者影响 | `knowledge/musl-glibc-developer-impact.md` |
| 可移植打包指南 | `knowledge/packaging.md` |
| 鸿蒙特有机制汇总 | `knowledge/harmonyos-specifics.md` |

### 6.2 档案命名规范

- 补丁文件：`NNNN-description.patch`（四位序号 + 描述）
- 报告文件：`{type}-report.md`
- 脚本文件：小写 + 连字符，如 `build.sh`

### 6.3 版本兼容性评估

当检索到相似版本时，评估补丁可复用性：

| 版本差异 | 可复用性 | 说明 |
|----------|----------|------|
| 补丁版本 | 高 | 通常是 bug 修复 |
| 小版本升级 | 中 | API 兼容，可能需要调整 |
| 大版本升级 | 低 | 可能需要重新适配 |

### 6.4 软链接处理规范（强制）

> **⚠️ 强制规范**：鸿蒙系统的 SELinux 策略限制软链接的创建和访问。在编译、安装、验证的各个阶段都必须正确处理软链接问题。

**核心原则**：
1. **不能仅检查软链接是否存在**，必须验证是否可执行
2. **禁止使用 `ln -sf` 覆盖已存在的软链接**（会创建带随机后缀的文件）
3. **必须使用 `rm -f` + `ln -s` 的方式创建软链接**
4. **软链接不可用时必须使用规避方式**：wrapper 脚本（推荐）或 cp 复制
5. **make install 后必须检查**安装产物中的软链接

**详细规范**：参考 `knowledge/environment.md` 第 9 节

**快速参考**：
```bash
# 创建软链接的正确方式（关键！）
rm -f /path/to/link           # 先删除
ln -s /target /path/to/link   # 再创建（不加 -f）

# 检查软链接
check_symlink "/path/to/link" || create_wrapper "name" "/path/to/target"

# 创建 wrapper 脚本（规避方案）
cat > $HOME/usr/local/bin/cc << 'EOF'
#!/bin/sh
exec /data/service/hnp/bin/clang "$@"
EOF
chmod +x $HOME/usr/local/bin/cc
```

> **关于 clang 路径问题**：鸿蒙的 clang 脚本使用 `exec -a` 设置 argv[0]，所以软链接和 wrapper 脚本都能正确找到 sysroot 和资源目录，不存在路径问题。

## 7. License

本技能遵循 MIT 许可证。�可证。�能遵循 MIT 许可证。