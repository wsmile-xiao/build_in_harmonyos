# 鸿蒙编译最佳实践

本文档整理了在鸿蒙系统上编译软件的最佳实践和方法论。

## 1. 三目录法（补丁开发）

### 1.1 目录结构

进行补丁开发时，推荐使用"三目录法"来管理代码：

```
project-x.y.z-orig/     # 原始源码（只读，用于对比和重新打补丁）
project-x.y.z-work/     # 工作目录（修改代码，开发补丁）
project-x.y.z-test/     # 测试目录（验证补丁是否正确应用）
```

### 1.2 完整工作流程

```bash
# 1. 解压并创建目录
tar -xf project-x.y.z.tar.xz
mv project-x.y.z project-x.y.z-orig
cp -a project-x.y.z-orig project-x.y.z-work

# 2. 在 work 目录开发修改
cd project-x.y.z-work
# ... 进行修改 ...

# 3. 生成补丁（使用 -U 参数扩大上下文）
diff -U 10 -r ../project-x.y.z-orig . > ../0001-port-for-ohos.patch
# 或针对单个文件
diff -U 10 ../project-x.y.z-orig/src/foo.c src/foo.c > ../fix-xxx.patch

# 4. 验证补丁
cp -a ../project-x.y.z-orig ../project-x.y.z-test
cd ../project-x.y.z-test
patch -p1 < ../0001-port-for-ohos.patch

# 5. 编译验证
./configure --prefix=$HOME/usr/local
make && make install
```

### 1.3 补丁生成规范

**上下文参数选择**：

| 参数 | 上下文行数 | 适用场景 |
|------|------------|----------|
| `-u` (默认) | 3 行 | 简单修改，代码唯一性强 |
| `-U 5` | 5 行 | 中等复杂度修改 |
| `-U 10` | 10 行 | 复杂修改，或代码有相似片段 |
| `-U 15` | 15 行 | 非常复杂修改，确保定位准确 |

**推荐使用 `-U 10`**，避免相似代码导致补丁应用错位。

### 1.4 补丁验证清单

```bash
# 验证补丁可以干净应用
patch --dry-run -p1 < patch.diff

# 实际应用
patch -p1 < patch.diff

# 检查结果
# ✅ 正确: patching file src/foo.c
# ❌ 错误: Hunk #1 FAILED at 123
```

**常见问题及解决**：

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `Hunk #1 FAILED` | 上下文不匹配 | 使用 `-U 10` 扩大上下文 |
| `patch unexpectedly ends` | 补丁文件损坏 | 重新生成补丁 |
| `Reversed (or previously applied)` | 补丁已应用 | 恢复原始文件后重试 |
| `can't find file to patch` | 路径不正确 | 检查 `-p` 参数 |

---

## 2. 编译前检查清单

在鸿蒙系统上编译任何软件前，建议按以下顺序检查：

### 2.1 环境检查

```bash
# 1. 系统信息
uname -s    # 应显示 HarmonyOS
uname -m    # 架构：aarch64
uname -r    # 内核版本

# 2. 编译器
which clang clang++
clang --version

# 3. LLVM 工具链
which llvm-ar llvm-ranlib llvm-nm llvm-strip

# 4. 环境变量
echo $CC $CXX $AR $RANLIB

# 5. 预定义宏
clang -dM -E - < /dev/null | grep OHOS

# 6. 临时目录（鸿蒙 /tmp 不可写）
export TMPDIR=$HOME/tmp
mkdir -p $TMPDIR
```

### 2.2 依赖检查

```bash
# 检查必需依赖
ls -la $HOME/usr/local/lib/libz.so
ls -la $HOME/usr/local/lib/libssl.so
ls -la $HOME/usr/local/lib/libncursesw.so

# 使用 pkg-config
pkg-config --exists zlib && echo "zlib OK"
pkg-config --exists openssl && echo "openssl OK"
```

### 2.3 工具兼容性检查

```bash
# 检查 sed 类型
sed --version 2>&1 | head -1
# GNU sed: sed (GNU sed) 4.9
# toybox: (无版本信息)

# 检查 expr 类型
expr --version 2>&1 | head -1
# GNU: expr (GNU coreutils) 9.10
# toybox: (无版本信息)
```

### 2.4 编译前代码扫描

```bash
#!/bin/bash
# harmonyos_precompile_scan.sh - 编译前兼容性扫描

PROJECT_DIR="$1"

echo "=== HarmonyOS 兼容性扫描 ==="

# 1. 扫描 fstat 对 stdin/stdout 的调用
echo "1. 检查 fstat(stdin/stdout) 调用..."
grep -rn "fstat.*STDIN_FILENO\|fstat.*STDOUT_FILENO" "$PROJECT_DIR" 2>/dev/null && echo "⚠️ 需要处理 fstat 限制"

# 2. 扫描 /tmp 硬编码
echo "2. 检查 /tmp 硬编码路径..."
grep -rn '"/tmp"' "$PROJECT_DIR" 2>/dev/null && echo "⚠️ 应使用 \$TMPDIR"

# 3. 扫描 glibc FILE 结构访问
echo "3. 检查 glibc FILE 结构访问..."
grep -rn "_IO_.*_ptr\|__freadptr" "$PROJECT_DIR" 2>/dev/null && echo "⚠️ musl FILE 不透明，需要适配"
```

---

## 3. 归档文档规范

### 3.1 README.md 必须包含的内容

| 章节 | 内容 | 重要性 |
|------|------|--------|
| 概述 | 软件简介 | ⭐⭐ |
| 软件信息 | 名称、版本、下载地址 | ⭐⭐⭐ |
| 鸿蒙环境 | 系统版本、编译器、工具链 | ⭐⭐ |
| 编译步骤 | 解压、打补丁、配置、编译、安装 | ⭐⭐⭐ |
| 补丁说明 | **修改文件列表 + 技术细节** | ⭐⭐⭐ 关键 |
| 遇到的问题 | 问题现象、原因分析、解决方案 | ⭐⭐⭐ 关键 |
| 经验总结 | 注意事项、与其他软件的关联 | ⭐⭐ |
| 参考资料 | 官方文档、相关项目 | ⭐ |

### 3.2 补丁说明章节要求

必须详细解释每个修改的技术原因：

```markdown
### 补丁说明

#### 修改文件
1. **config.guess**: 添加 HarmonyOS 系统检测
2. **config.sub**: 添加 ohos 操作系统支持

#### 关键修改详解

##### config.guess - 系统检测

**问题背景**: 原始 config.guess 无法识别 HarmonyOS

**技术原理**: 
- 通过 `uname -s` 检测系统名称
- 生成三元组 `aarch64-unknown-linux-ohos`

**解决方案**:
在系统识别 case 分支中添加：
```bash
*:HarmonyOS:*:*)
    GUESS=$UNAME_MACHINE-unknown-linux-ohos
    ;;
```

**影响**: 让 autotools 项目能够自动识别 HarmonyOS
```

### 3.3 manifest.yaml 规范

每个软件档案必须包含 `manifest.yaml`：

```yaml
software: openssl
version: 1.1.1w
status: success
build_system: custom-perl
compile_date: 2024-03-22

dependencies:
  required: [perl]
  optional: [zlib]

build_config:
  target: openharmony-aarch64
  configure_options:
    - --prefix=$HOME/usr/local
    - no-asm

patches_applied:
  - file: 0001-support-build-in-harmonyos.patch
    purpose: 添加 HarmonyOS 平台配置
    lines_changed: 120

compatibility:
  level: high
  issues: []
  notes: 核心功能正常

test_results:
  type: manual
  passed: 29
  failed: 6

knowledge_gained:
  - 使用 no-asm 禁用汇编优化避免 BAD_SIGNATURE
```

---

## 4. 问题排查方法论

### 4.1 排查流程

```
错误发生
    │
    ├─► 收集错误信息
    │       - 完整错误输出
    │       - 编译日志
    │       - 环境变量
    │
    ├─► 分析错误类型
    │       ├─► 编译错误 → 检查编译器/标志/头文件
    │       ├─► 链接错误 → 检查库依赖
    │       ├─► 运行时错误 → 检查系统限制
    │       └─► 配置错误 → 检查构建系统适配
    │
    ├─► 搜索已有知识
    │       - knowledge/error-patterns.md
    │       - archives/{软件}/README.md
    │
    └─► 记录解决方案
            - 更新 manifest.yaml
            - 更新 README.md
```

### 4.2 常用诊断命令

```bash
# 查看二进制依赖
llvm-readelf -d /path/to/binary | grep NEEDED

# 查看符号
llvm-nm /path/to/library

# 检查库链接
ldd /path/to/binary

# 追踪系统调用
strace -f /path/to/binary

# 检查 SELinux 上下文
ls -Z /path/to/file
```

---

## 5. 编译选项建议

### 5.1 必须的编译选项

```bash
# 所有库都必须使用 -fPIC
export CFLAGS="-fPIC -O2"
export CXXFLAGS="-fPIC -O2"

# 设置库路径
export LDFLAGS="-L$HOME/usr/local/lib"
export LIBRARY_PATH=$HOME/usr/local/lib:$LIBRARY_PATH
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
```

### 5.2 编译器设置

```bash
export CC=clang
export CXX=clang++
export AR=llvm-ar
export RANLIB=llvm-ranlib
export NM=llvm-nm
export STRIP=llvm-strip
```

### 5.3 特殊选项

| 软件类型 | 特殊选项 | 原因 |
|----------|----------|------|
| OpenSSL | `no-asm` | 避免 ARM64 汇编 bug |
| ncurses | `--enable-overwrite` | 头文件安装到顶层 |
| readline | `--with-shared` | 生成共享库 |

### 5.4 ⭐ 静态库优先原则

**背景**：鸿蒙系统某些关键组件（如 `/bin/zsh`）依赖系统共享库。用户编译的共享库可能与之冲突，导致系统不稳定。

**核心原则**：

| 库类型 | 编译选项 | 适用场景 | 风险 |
|--------|----------|----------|------|
| **静态库** | `--without-shared` | 系统关键依赖的库 | ✅ 安全，推荐 |
| 共享库 | `--with-shared` | 新库，不影响系统 | ⚠️ 需谨慎检查 |

**判断标准**：

```bash
# 1. 检查系统是否已有同名共享库
ldd /bin/zsh | grep ncurses
# 输出: libncursesw.so.6 => /system/lib64/libncursesw.so.6

# 2. 如果系统已有，优先使用静态库
./configure --without-shared  # ⭐ 推荐

# 3. 如果是新库，不影响系统组件，可以考虑共享库
./configure --with-shared
```

**典型案例**：

| 库名 | 系统依赖 | 推荐编译方式 | 原因 |
|------|----------|--------------|------|
| ncurses | `/bin/zsh` 依赖 | `--without-shared` | 避免 Shell 崩溃 |
| readline | 无系统依赖 | `--with-shared` | 可共享使用 |
| openssl | 无系统依赖 | `--with-shared` | 可共享使用 |
| zlib | 无系统依赖 | `--with-shared` | 可共享使用 |

**静态链接的好处**：

1. **避免库冲突**：不干扰系统共享库
2. **运行时不依赖**：可执行文件自包含
3. **部署简单**：不需要管理 LD_LIBRARY_PATH
4. **稳定性高**：不受系统库更新影响

**静态链接的注意事项**：

```bash
# Python 扩展模块静态链接示例
clang -shared -L. -lpython3.9 \
    _cursesmodule.o \
    $HOME/usr/local/lib/libncursesw.a \  # 静态链接
    -o _curses.so

# 验证链接
llvm-readelf -d _curses.so | grep NEEDED
# 应该不包含 libncursesw.so
```

---

## 6. 工作流程经验总结

### 6.1 编译新软件推荐流程

```
1. 环境准备
   ├── 检查 PATH 包含 $HOME/usr/local/bin
   ├── 设置 TMPDIR=$HOME/tmp
   └── 确认已安装 GNU coreutils 和 GNU sed

2. 源码准备
   ├── 下载源码包
   ├── 创建 orig/work/test 三个目录
   └── 在 work 目录中进行修改

3. 适配修改
   ├── 识别构建系统类型
   ├── 修改 config.guess/config.sub（Autotools）
   ├── 处理其他兼容性问题
   └── 验证编译成功

4. 补丁生成
   ├── 对比 orig 和 work 生成补丁
   ├── 在 test 目录验证补丁
   └── 确认补丁正确

5. 归档文档
   ├── 编写 README.md（详细技术解释）
   ├── 创建 manifest.yaml
   ├── 检查归档目录命名
   └── 更新索引
```

### 6.2 常见错误避免

| 错误 | 后果 | 正确做法 |
|------|------|----------|
| 跳过验证步骤 | 补丁无法应用 | 每次修改后都验证编译 |
| 直接写补丁文件 | 补丁格式错误 | 使用三目录法生成 |
| README 缺少技术细节 | 无法复现和参考 | 详细记录问题分析 |
| 忘记设置 TMPDIR | configure 失败 | 先设置再编译 |
| 忽略工具兼容性 | 隐蔽的 bug | 优先安装 GNU 工具 |

---

---

## 7. 版本升级时补丁偏移与维护策略

### 7.1 问题描述

当软件升级版本（如从 3.9.0 升级到 3.9.18）时，原有补丁可能因为源码目录结构变化、
代码行数增减、文件重命名等原因导致 `patch` 命令失败（`Hunk #N FAILED`）。

### 7.2 根因分析

补丁偏移的主要原因：

| 原因 | 说明 | 严重程度 |
|------|------|----------|
| **目录结构变化** | 新版本增加/删除/重命名目录 | 🔴 高 |
| **代码行数变化** | 上游修改导致上下文匹配失败 | 🟡 中 |
| **文件内容重构** | 函数拆分/合并/移动到其他文件 | 🔴 高 |
| **格式化变化** | 缩进风格、换行符差异 | 🟢 低 |
| **补丁冲突** | 上游已修复相同问题 | 🟢 低（可跳过） |

### 7.3 补丁维护策略

**策略 1：最小化补丁（推荐）**

```bash
# 每个补丁只做最小必要的修改
# 好的补丁：只修改 HarmonyOS 相关的 5 行
# 差的补丁：重写整个 200 行函数

# 补丁生成时使用较大上下文（-U 10），降低偏移风险
diff -U 10 -r orig/ work/ > 0001-fix-for-ohos.patch
```

**策略 2：语义化补丁而非行级补丁**

```bash
# 不要依赖具体行号，而是依赖代码上下文
# 使用 -U 10 或更大的上下文让 patch 工具有更多匹配信息

# 检查补丁是否可以应用
patch --dry-run -p1 < 0001-fix-for-ohos.patch
```

**策略 3：版本升级工作流程**

```bash
# 1. 尝试应用旧补丁
cd new-version-src/
patch --dry-run -p1 < ../old-patches/*.patch 2>&1 | grep FAILED

# 2. 如果有 FAILED，手动定位修改点
# 搜索关键字符串（如 __OHOS__、HAVE_XXX）在新版本中的位置
grep -rn "__OHOS__\|HAVE_LOG_SYSLOG\|/* HarmonyOS" .

# 3. 手动应用修改或使用 patch 的 fuzz factor
patch -p1 -F 3 < ../old-patches/0001-fix-for-ohos.patch

# 4. 重新生成补丁
diff -U 10 -r ../new-version-src-orig/ . > 0001-fix-for-ohos.patch
```

**策略 4：补丁文档化**

每个补丁文件头部必须说明修改的**语义意图**而非具体行号：

```diff
# 好的补丁头部
# Description: Disable syslog on HarmonyOS (syscall not implemented)
# File: src/foo.c
# Search for: AC_CHECK_FUNCS([syslog])
# Replace with: #ifdef __OHOS__ guard

# 差的补丁头部
# Changed line 1234 in src/foo.c
```

### 7.4 预防措施

```bash
# 在 Makefile 或构建脚本中添加版本检查
if [ "$VERSION" != "3.9.0" ]; then
    echo "⚠️ Warning: patches were developed for version 3.9.0"
    echo "   Current version: $VERSION"
    echo "   Some patches may need manual adjustment"
fi
```

### 7.5 影响范围

所有需要维护补丁的软件档案。补丁数量越多、修改范围越大，版本升级时的维护成本越高。

### 相关知识

- [best-practices.md §1](#1-三目录法补丁开发) — 三目录法（补丁开发基础）
- [autotools-patterns.md §9.1](autotools-patterns.md#91-configure-后子目录-makefile-包含乱码) — configure 后 Makefile 乱码
- [build-systems.md §10.3](build-systems.md#103-automake-版本不匹配) — automake 版本不匹配

> 来源：`archives/p/python/3.9.0/manifest.yaml`

---

*文档版本: 1.2*  
*最后更新: 2026-03-30*
*新增 §7：版本升级时补丁偏移与维护策略（跨软件知识）*