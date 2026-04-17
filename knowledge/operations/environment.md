# 鸿蒙系统环境特性

> **完整 sudo 分析**（权限模型、功能覆盖、编译影响）：→ `sudo-analysis.md`

## 1. 系统信息

| 项目 | 值 |
|------|-----|
| 系统名称 | HarmonyOS / OpenHarmony |
| 内核 | HongMeng Kernel |
| 架构 | aarch64 (主要), arm, x86_64 |
| C 库 | musl libc |

## 1.5 开发环境三件套

鸿蒙开发环境由三个核心组件构成，需要从**应用市场**安装：

| 组件 | 获取方式 | 提供的能力 |
|------|----------|-----------|
| **DevBox** | 应用市场搜索 "DevBox" | 编译工具链（clang、llvm-ar、patchelf、binary-sign-tool 等），安装在 `/data/service/hnp/bin/` |
| **GitNext** | 应用市场搜索 "GitNext" | git 版本管理工具 |
| **HiShell** | 系统内置 | 设备上的终端环境，`/bin/sh` 是 toybox ash |

### 关键认知

- **HiShell ≠ bash**：`/bin/sh` 是 toybox ash，不支持 `${BASH_SOURCE}`、`[[ ]]`、数组等 bash 特性
- **工具链来自 DevBox**：`/data/service/hnp/bin/` 下的工具由 DevBox 提供，不是系统自带
- **git 来自 GitNext**：通过应用市场安装 GitNext 获取 git，不在系统预装路径中
- **所有命令在 HiShell 中执行**：编译、运行、打包等操作均在 HiShell 终端中完成

## 2. 编译工具链

### 2.1 编译器

| 工具 | 路径 | 版本 |
|------|------|------|
| clang | /data/service/hnp/bin/clang | 15.0.4 |
| clang++ | /data/service/hnp/bin/clang++ | 15.0.4 |

### 2.2 LLVM 工具链

鸿蒙使用 LLVM 工具链替代 GNU 工具：

| GNU 工具 | LLVM 替代 | 用途 |
|----------|-----------|------|
| ar | llvm-ar | 静态库管理 |
| ranlib | llvm-ranlib | 库索引 |
| nm | llvm-nm | 符号表查看 |
| strip | llvm-strip | 符号移除 |
| objdump | llvm-objdump | 反汇编 |
| objcopy | llvm-objcopy | 对象文件操作 |

### 2.3 其他工具

| 工具 | 版本 | 状态 |
|------|------|------|
| make | GNU Make 4.4.1 | ✅ 可用 |
| cmake | 4.1.2 | ✅ 可用 |
| autoconf | 2.72 | ✅ 可用 |
| perl | 5.42.0 | ✅ 可用 |
| git | 2.45.2 | ✅ 可用 |

## 3. 预定义宏

Clang 在鸿蒙系统上自动定义以下宏：

```c
__OHOS__           // OpenHarmony 系统标识（官方标准）
__OHOS_FAMILY__    // OpenHarmony 家族标识
__OHOS_Major__     // 主版本号
```

**验证方式**：
```bash
clang -dM -E - < /dev/null | grep OHOS
```

## 4. 环境变量配置

> **重要**：以下环境变量对编译成功率有决定性影响，必须在编译前配置！

### 4.1 必须配置的环境变量

```bash
# ============================================================
# 鸿蒙编译环境必备配置 - 添加到 ~/.zshrc
# ============================================================

# 安装前缀
export DEFAULT_PREFIX=$HOME/usr/local

# PATH（确保用户安装的工具优先）
export PATH=$DEFAULT_PREFIX/bin:$HOME/npm/bin:$HOME/.local/bin:$PATH

# 库路径（运行时）
export LD_LIBRARY_PATH=$DEFAULT_PREFIX/lib:$LD_LIBRARY_PATH

# pkg-config 路径（⭐ 头文件和库路径通过 pkg-config 发现，不要设置 C_INCLUDE_PATH）
# 详见本文件 §11「头文件搜索路径：PKG_CONFIG_PATH vs C_INCLUDE_PATH」
export PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig:$PKG_CONFIG_PATH

# CMake 搜索路径（现代 C/C++ 项目常用）
export CMAKE_PREFIX_PATH=$DEFAULT_PREFIX${CMAKE_PREFIX_PATH:+:$CMAKE_PREFIX_PATH}

# 编译器设置（使用 LLVM 工具链）
export CC="clang"
export CXX="clang++"
export AR="llvm-ar"
export RANLIB="llvm-ranlib"
export NM="llvm-nm"
export STRIP="llvm-strip"

# ⭐ 关键：所有编译都使用 -fPIC（musl BIND_NOW 要求）
export CFLAGS="-fPIC -O2"
export CXXFLAGS="-fPIC -O2"
export LDFLAGS="-L$DEFAULT_PREFIX/lib"

# 临时目录（鸿蒙 /tmp 只读，必须设置）
export TMPDIR=$HOME/tmp

# 创建必要目录
mkdir -p $TMPDIR
mkdir -p $DEFAULT_PREFIX/{bin,lib,include,share}
```

### 4.2 环境变量作用说明

| 变量 | 作用 | 不设置的后果 |
|------|------|--------------|
| `TMPDIR` | 临时文件目录 | Autotools 崩溃（/tmp 只读） |
| `CC/CXX` | 指定编译器 | 可能使用错误的编译器 |
| `CFLAGS="-fPIC"` | 位置无关代码 | musl BIND_NOW 导致符号找不到 |
| `AR/RANLIB` | 静态库工具 | 使用 GNU ar 导致格式不兼容 |
| `LD_LIBRARY_PATH` | 运行时库路径 | 找不到用户安装的库 |
| `PKG_CONFIG_PATH` | pkg-config 搜索路径 | 找不到已安装的库 |
| `CMAKE_PREFIX_PATH` | CMake 搜索路径 | CMake 项目找不到自定义安装的软件 |

> ⚠️ **不要设置 `C_INCLUDE_PATH`**：详见 §11，该变量会与 pkg-config 冲突，导致 `pkg-config --cflags` 返回空。
>
> ⚠️ **不要设置 `LIBRARY_PATH`**：GCC 链接器全局搜索路径，会与构建系统冲突。需要指定库路径时应使用 `LDFLAGS="-L..."` 或 `PKG_CONFIG_PATH`。

### 4.3 便捷别名

```bash
alias configure='./configure --prefix=$DEFAULT_PREFIX'
alias cmake='cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX'
alias Configure='./Configure --prefix=$DEFAULT_PREFIX'
```

### 4.4 环境检查脚本

每次编译前运行以下检查：

```bash
#!/bin/bash
# ohc-run.py check-env - 鸿蒙编译环境检查

echo "=== 必要环境变量 ==="
test -n "$TMPDIR" && echo "✅ TMPDIR=$TMPDIR" || echo "❌ TMPDIR 未设置"
test -n "$CC" && echo "✅ CC=$CC" || echo "⚠️ CC 未设置"
test -n "$CFLAGS" && echo "✅ CFLAGS=$CFLAGS" || echo "⚠️ CFLAGS 未设置"

echo ""
echo "=== 必要目录 ==="
test -d "$TMPDIR" && echo "✅ $TMPDIR 存在" || echo "❌ $TMPDIR 不存在"
test -d "$DEFAULT_PREFIX/bin" && echo "✅ $DEFAULT_PREFIX/bin 存在" || echo "❌ 安装目录不存在"

echo ""
echo "=== 编译器 ==="
command -v cc >/dev/null && echo "✅ cc: $(cc --version | head -1)" || echo "❌ cc 不存在"
command -v clang >/dev/null && echo "✅ clang: $(clang --version | head -1)" || echo "❌ clang 不存在"
```

## 5. 系统限制

<!-- ~~### 5.1 文件系统~~ → 已迁移至 graph/E002.kv, E018.kv, E050.kv, E073.kv, E008.kv -->

<!-- ~~### 5.2 SELinux 域转换~~ → 已迁移至 graph/E009.kv + doc/E009.md -->

<!-- ~~#### FIFO 创建限制~~ → 已迁移至 graph/E074.kv + doc/E074.md -->

<!-- ~~#### chmod +x 限制~~ → 已迁移至 graph/E046.kv + doc/E046.md -->

<!-- ~~#### /proc 文件系统访问限制~~ → 已迁移至 graph/E031.kv + doc/E031.md -->

<!-- ~~#### /usr/bin/env 不存在~~ → 已迁移至 graph/E037.kv + doc/E037.md -->

> ✅ **HongMeng Kernel 1.12.0 已解决**：`/usr/bin/env` 现已存在（指向 toybox 的符号链接），`#!/usr/bin/env xxx` shebang 写法可用。

<!-- ~~#### CA 证书包缺失~~ → 已迁移至 graph/E034.kv + doc/E034.md -->

## 6. 三元组格式

鸿蒙系统的标准三元组：

```
<架构>-unknown-linux-ohos
```

示例：
- `aarch64-unknown-linux-ohos`
- `arm-unknown-linux-ohos`
- `x86_64-unknown-linux-ohos`

<!-- ~~## 7. 系统检查命令~~ → 已迁移至各对应条目 doc/*.md（详见 best-practices.md §4.2） -->

<!-- ~~## 8. 与 Linux 的主要差异~~ → 已迁移至各对应条目（E002,E001/E012,E002,E009,E018,E037,E034,E031） -->

## 9. 软链接处理规范（强制）

> **重要**：鸿蒙系统的 SELinux 策略限制软链接的创建和访问。在编译、安装、验证的各个阶段都必须正确处理软链接问题。

### 9.1 问题特征

```bash
# 软链接存在但无法执行
ls -la cc -> /data/service/hnp/bin/clang
cc --version
# /bin/sh: cc: No such file or directory

# ln -sf 创建带随机后缀的文件（关键问题！）
ln -sf target link
ls -la link_XXXXXX  # 出现带后缀的文件
```

### 9.1.1 ln -sf 的问题

> **⚠️ 重要发现**：在鸿蒙系统上，`ln -sf` 覆盖已存在的软链接时会创建带随机后缀的文件，这是 SELinux 策略导致的特殊行为。

```bash
# 错误做法：ln -sf 覆盖已存在的软链接
ln -sf /target /path/to/link
# 结果：创建了 link_XXXXXX 带随机后缀的文件

# 正确做法：先删除再创建
rm -f /path/to/link
ln -s /target /path/to/link
```

> ✅ **HongMeng Kernel 1.12.0 已解决**：`ln -sf` 不再创建带随机后缀的文件，覆盖操作正常工作。但建议保留 `rm -f && ln -s` 作为最佳实践。

### 9.2 软链接可用性检查函数

```bash
# ⚠️ 强制规范：必须使用此函数检查软链接
check_symlink() {
    local link=$1
    local desc=${2:-"工具"}

    # 1. 文件不存在
    if [ ! -e "$link" ]; then
        echo "❌ $desc 不存在: $link"
        return 1
    fi

    # 2. 检查是否为软链接
    if [ -L "$link" ]; then
        local target=$(readlink "$link")

        # 3. 验证软链接是否可执行（关键！）
        if "$link" --version >/dev/null 2>&1; then
            echo "✅ $desc 软链接可用: $link -> $target"
            return 0
        else
            echo "❌ $desc 软链接不可用（SELinux 限制）: $link -> $target"
            return 2  # 特殊返回码：需要规避
        fi
    fi

    # 4. 普通文件
    if [ -x "$link" ]; then
        echo "✅ $desc 可执行: $link"
        return 0
    fi

    echo "❌ $desc 不可执行: $link"
    return 1
}
```

### 9.3 软链接规避方案

**方案1：wrapper 脚本（推荐）**

```bash
# 优点：简单可靠，不复制大文件
create_wrapper() {
    local name=$1
    local target=$2
    local bindir=${3:-$HOME/usr/local/bin}

    cat > "$bindir/$name" << EOF
#!/bin/sh
exec $target "\$@"
EOF
    chmod +x "$bindir/$name"
    echo "✅ 创建 wrapper: $bindir/$name -> $target"
}

# 使用示例
create_wrapper "cc" "/data/service/hnp/bin/clang"
create_wrapper "c++" "/data/service/hnp/bin/clang++"
```

**方案2：复制文件**

```bash
# 适用于目标文件较小的情况
cp $(readlink -f /path/to/target) /path/to/link
```

### 9.4 标准处理流程

```bash
# ⚠️ 强制规范：在任何涉及软链接的操作中使用此流程
setup_tool_symlink() {
    local name=$1      # 工具名称，如 cc
    local target=$2    # 目标路径，如 /data/service/hnp/bin/clang
    local bindir=${3:-$HOME/usr/local/bin}

    # 1. 先删除已存在的文件（关键！不能用 ln -sf）
    rm -f "$bindir/$name"

    # 2. 创建软链接（不加 -f）
    ln -s "$target" "$bindir/$name"

    # 3. 验证软链接是否可用
    if [ -L "$bindir/$name" ]; then
        if "$bindir/$name" --version >/dev/null 2>&1; then
            echo "✅ $name 软链接可用"
            return 0
        else
            echo "⚠️ $name 软链接不可用，创建 wrapper 脚本"
            rm -f "$bindir/$name"
            create_wrapper "$name" "$target" "$bindir"
        fi
    fi
}
```

> **注意**：鸿蒙系统上 `ln -sf` 覆盖已存在的软链接会创建带随机后缀的文件，必须使用 `rm -f` + `ln -s` 的方式。

### 9.5 应用场景

| 阶段 | 场景 | 处理方式 |
|------|------|----------|
| Phase 2 | 检查依赖工具 | `check_symlink` + `create_wrapper` |
| Phase 3 | make install 后 | 检查所有安装的软链接 |
| Phase 4 | 验证产物 | 必须验证可执行性，不仅检查存在 |
| 日常使用 | 手动创建软链接 | 优先使用 wrapper 脚本 |

### 9.6 常见问题

**Q: 为什么 `ls -la` 显示软链接存在，但执行报错？**

A: SELinux 策略限制了用户进程对软链接指向文件的访问。软链接本身存在，但跟随（follow）软链接访问目标文件时被拒绝。

**Q: 为什么有时候软链接能用，有时候不能？**

A: 取决于 SELinux context。不同进程、不同目录可能有不同的权限策略。

**Q: wrapper 脚本有什么优势？**

A:
1. 不依赖软链接，避免 SELinux 问题
2. 不需要复制大文件，节省空间
3. 可以添加额外参数或环境变量
4. 简单可靠，易于维护

## 10. Perl 本地模块库配置

### 配置本地 Perl 模块路径

```bash
# 添加到 ~/.zshrc
export PERL5LIB="$HOME/perl-lib/lib/perl5:$PERL5LIB"
```

### 已安装的 Perl 模块

| 模块 | 版本 | 用途 |
|------|------|------|
| HTTP::Daemon | 6.16 | HTTP 服务器模拟 |
| HTTP::Message | 6.18 | HTTP 消息处理 |
| HTTP::Date | 6.06 | HTTP 日期处理 |
| URI | 5.27 | URL 解析 |
| Encode::Locale | 1.05 | 编码本地化 |
| Try::Tiny | 0.31 | 异常处理 |
| IO::HTML | 1.004 | HTML 文件读取 |
| LWP::MediaTypes | 6.04 | 媒体类型处理 |

### 安装新 Perl 模块

```bash
# 方法1：下载 cpanm
curl -L https://cpanmin.us -o /tmp/cpanm
perl /tmp/cpanm --notest -l ~/perl-lib Module::Name

# 方法2：手动安装
curl -LO https://cpan.metacpan.org/authors/id/.../Module-X.XX.tar.gz
tar xf Module-X.XX.tar.gz
cd Module-X.XX
perl Makefile.PL INSTALL_BASE=$HOME/perl-lib
make && make install
```

<!-- ~~## 11. 头文件搜索路径：PKG_CONFIG_PATH vs C_INCLUDE_PATH~~ → 已迁移至 graph/E075.kv + doc/E075.md -->
v + doc/E075.md -->
