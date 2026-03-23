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
3. 创建软件档案：
   - 生成补丁文件
   - 创建 manifest.yaml
   - 编写 README.md
   - 记录测试报告

### 3.2 知识检索策略

| 检索场景 | 检索路径 | 用途 |
|----------|----------|------|
| 精确软件版本 | `archives/{letter}/{name}/{version}/` | 复用完整方案 |
| 相似版本 | `archives/{letter}/{name}/` | 评估补丁兼容性 |
| 构建系统知识 | `knowledge/build-systems.md` | 适配策略 |
| 环境配置 | `knowledge/environment.md` | 系统特性 |
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
│   ├── environment.md          # 鸿蒙环境特性
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
| 环境检查 | `knowledge/environment.md` |
| 常见问题 | `knowledge/troubleshooting.md` |
| musl 兼容性 | `knowledge/musl-compat.md` |
| 问题案例 | `knowledge/error-patterns.md` |

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

本技能遵循 MIT 许可证。