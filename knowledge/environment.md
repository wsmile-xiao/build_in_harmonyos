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
# check-env.sh - 鸿蒙编译环境检查

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

### 5.1 文件系统

> **完整文件系统架构分析**: 详见 `filesystem-analysis.md`，涵盖 HMFS/HMDFS/EROFS/devfs 等全部文件系统类型、根目录布局差异、Hmmac 安全层等。

| 限制 | 说明 | 解决方案 |
|------|------|----------|
| `/tmp` 不可写 | erofs 只读挂载 | `export TMPDIR=$HOME/tmp` |
| 软链接访问受限 | SELinux + Hmmac 策略 | 使用 `cp` 或 wrapper 脚本替代 `ln -s`，详见 §9 |
| `fstat(pipe)` 返回 EACCES | 安全限制 | 使用兼容性封装 |
| `$HOME` 是 HMDFS 分布式文件系统 | `stat -f` 返回 unknown，flock 语义可能不同 | 编译脚本避免依赖 FS 类型检测 |
| 无 `/usr`、`/var`、`/run`、`/sbin` | FHS 标准目录缺失 | 自建目录结构或写入 `$HOME` |

### 5.2 SELinux 域转换

用户进程执行 SDK 工具时会触发域转换：

```
hishell_hap:s0 → adhoc_bin:s0 → 无法执行 hnp_file
```

**解决方案**：使用管道语法绕过
```bash
# 直接执行失败
clang --version

# 管道执行成功
clang --version | cat
```

#### FIFO 创建限制

鸿蒙 SELinux 策略禁止用户进程创建 FIFO（命名管道），这会影响 GNU make 的 jobserver 机制：

```bash
# make -j2 会失败，因为 jobserver 依赖 FIFO
make -j2  # 可能卡住或报错

# 解决方案：使用单线程
make -j1  # 强制单线程，不使用 jobserver
```

**影响范围**：所有使用 `make -j` 并行构建的场景。鸿蒙上编译必须使用 `make -j1`。

**注意**：部分 `make check` 测试套件内部也依赖 FIFO，可能导致测试失败或挂起。

#### chmod +x 限制

鸿蒙 SELinux 策略可能限制 `chmod +x` 操作，导致编译生成的二进制文件无法直接执行。

```bash
# chmod +x 可能不生效
chmod +x script.sh
./script.sh  # Permission denied

# 解决方案：使用 sh 直接执行
sh script.sh
```

#### /proc 文件系统访问限制

鸿蒙 SELinux 策略限制普通用户访问 /proc 文件系统：

```bash
# /proc/stat 普通用户不可读
cat /proc/stat  # Permission denied

# htop 等工具需要 sudo 运行
sudo -E TERM=xterm-256color htop
```

> **注意**：鸿蒙 sudo 是极简自研实现，**不支持 `-E` 选项**，上面的命令实际会失败。详见 `sudo-analysis.md` §8。
> 
> 实际可行方案：
> ```bash
> # 方案1：合并为单条 sudo 命令
> sudo sh -c 'export TERM=xterm-256color; htop'
> # 方案2：如果 htop 的固定 PATH 已包含所需路径，直接运行
> sudo htop
> ```

**受影响的工具**：htop、top、任何依赖 /proc 的诊断工具
**解决方案**：使用 sudo 运行（需要保留环境变量）

#### /usr/bin/env 不存在

鸿蒙系统没有 `/usr/bin/env`，使用 `#!/usr/bin/env` shebang 的脚本会失败：

```bash
# 修复 shebang
sed -i 's|#!/usr/bin/env sh|#!/bin/sh|' script.sh
sed -i 's|#!/usr/bin/env perl|#!/usr/bin/perl|' script.pl

# 安装后批量检查
grep -rl '#!/usr/bin/env' $HOME/usr/local/bin/ 2>/dev/null
```

**受影响的软件**：libtool（libtoolize 脚本）、各种使用 env shebang 的工具

#### CA 证书包缺失

鸿蒙系统未预装 CA 证书包，HTTPS 验证会失败：

```bash
# 临时方案
wget --no-check-certificate https://example.com

# 检查
ls /etc/ssl/certs/ca-certificates.crt  # 不存在
```

**受影响的工具**：wget、curl、任何使用 OpenSSL 进行 HTTPS 验证的工具

## 6. 三元组格式

鸿蒙系统的标准三元组：

```
<架构>-unknown-linux-ohos
```

示例：
- `aarch64-unknown-linux-ohos`
- `arm-unknown-linux-ohos`
- `x86_64-unknown-linux-ohos`

## 7. 系统检查命令

```bash
# 系统信息
uname -s    # HarmonyOS
uname -m    # aarch64
uname -r    # 1.11.0

# 编译器
clang --version

# LLVM 工具
which llvm-ar llvm-ranlib llvm-nm

# 预定义宏
clang -dM -E - < /dev/null | grep -E "OHOS|GLIBC"
```

## 8. 与 Linux 的主要差异

| 方面 | Linux | HarmonyOS |
|------|-------|-----------|
| C 库 | glibc | musl libc |
| 编译器 | gcc | clang |
| ar | GNU ar | llvm-ar |
| /tmp | 可写 | 只读 |
| SELinux | 通常禁用 | 强制启用 |
| 软链接 | 正常 | 部分受限 |
| `/usr/bin/env` | 存在 | ❌ 不存在 |
| `/etc/ssl/certs/` | 预装 CA 证书 | ❌ 缺少 ca-certificates |
| `/proc/` 访问 | 普通用户可读 | ⚠️ SELinux 限制，需 sudo |
| **sudo** | 完整权限管理框架 | ⚠️ 极简提权开关，详见 `sudo-analysis.md` |

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

## 11. 头文件搜索路径：PKG_CONFIG_PATH vs C_INCLUDE_PATH

> **⚠️ 重要经验**：这是一个在实践中发现的典型误区，务必在编译初期就正确配置。

### 11.1 问题现象

在鸿蒙系统上，当设置了 `C_INCLUDE_PATH` 环境变量后，`pkg-config --cflags` 会返回空字符串：

```bash
# 已安装的 .pc 文件明确写了 Cflags
$ cat /storage/Users/currentUser/usr/local/lib/pkgconfig/openssl.pc
  Cflags: -I${includedir}

# 但 pkg-config --cflags 返回空！
$ pkg-config --cflags openssl
  （空）

# --debug 输出揭示了原因
$ pkg-config --debug --cflags openssl 2>&1
  Package libssl has -I/storage/Users/currentUser/usr/local/include in Cflags
  Removing -I/storage/Users/currentUser/usr/local/include from cflags for libssl
  returning flags string ""
```

**所有带 `Cflags:` 行的 .pc 包都受影响**（OpenSSL、zlib、libffi、sqlite3 等），不仅限于特定软件。

### 11.2 根因分析

pkg-config 的 `verify_package()` 函数在加载 .pc 文件后会执行"系统目录过滤"：

1. 读取 `PKG_CONFIG_SYSTEM_INCLUDE_PATH` 环境变量（或编译时内置默认值 `/usr/include`）
2. **额外读取 GCC 的环境变量**：`C_INCLUDE_PATH`、`CPATH`、`CPP_INCLUDE_PATH`
3. 遍历 Cflags 中的 `-I` 标志，如果路径匹配上述任一"系统目录"，则删除该标志
4. 如果未设置 `PKG_CONFIG_ALLOW_SYSTEM_CFLAGS=1`，则过滤生效

因此，当 `.pc` 文件中的 `includedir` 恰好等于 `C_INCLUDE_PATH` 中的路径时，对应的 `-I` 标志会被 pkg-config 视为"冗余的系统路径"而删除。

### 11.3 为什么不应该设置 C_INCLUDE_PATH

| 问题 | 说明 |
|------|------|
| **与 pkg-config 冲突** | pkg-config 会将 `C_INCLUDE_PATH` 中的路径视为系统目录，过滤掉所有匹配的 `-I` 标志 |
| **路径优先级不可控** | `C_INCLUDE_PATH` 是编译器预处理器级别的全局设置，无法针对不同项目区分 |
| **与构建系统冲突** | CMake、autotools、meson 各有自己的依赖查找机制，`C_INCLUDE_PATH` 可能干扰它们 |
| **非 Linux 标准做法** | Linux 上编译自定义安装的软件，标准做法是通过构建系统（pkg-config、CMake）发现依赖，而非设置编译器全局路径 |

### 11.4 正确做法：依赖构建系统发现依赖

**有 .pc 文件的库（绝大多数 C/C++ 库）**：只需设置 `PKG_CONFIG_PATH`

```bash
export PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig:$PKG_CONFIG_PATH
```

构建系统会自动调用 `pkg-config --cflags --libs` 获取正确的 `-I` 和 `-L` 参数。

**没有 .pc 文件的库**：

```bash
# 方式 A：CMake 项目（推荐）
cmake .. -DCMAKE_PREFIX_PATH=$DEFAULT_PREFIX
# 或更精确地
cmake .. -DCMAKE_INCLUDE_PATH=$DEFAULT_PREFIX/include \
         -DCMAKE_LIBRARY_PATH=$DEFAULT_PREFIX/lib

# 方式 B：Autotools 项目
./configure --prefix=$DEFAULT_PREFIX CPPFLAGS="-I$DEFAULT_PREFIX/include" LDFLAGS="-L$DEFAULT_PREFIX/lib"

# 方式 C：手动编译
clang -I$DEFAULT_PREFIX/include -L$DEFAULT_PREFIX/lib ... -o output
```

**注意**：`CPPFLAGS` 和 `LDFLAGS` 是构建系统级别的变量，不会影响 pkg-config 的系统目录判断逻辑，可以安全使用。

### 11.5 推荐的 .zshrc 配置

```bash
# ✅ 应该设置的环境变量
export PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}
export CMAKE_PREFIX_PATH=$DEFAULT_PREFIX${CMAKE_PREFIX_PATH:+:$CMAKE_PREFIX_PATH}
export LD_LIBRARY_PATH=$DEFAULT_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
export PATH=$DEFAULT_PREFIX/bin:$PATH

# ❌ 不要设置（会与 pkg-config 和构建系统冲突）
# export C_INCLUDE_PATH=$DEFAULT_PREFIX/include   # 会导致 pkg-config --cflags 返回空
# export CPLUS_INCLUDE_PATH=$DEFAULT_PREFIX/include
# export LIBRARY_PATH=$DEFAULT_PREFIX/lib
```

### 11.6 紧急修复

如果已经设置了 `C_INCLUDE_PATH` 且遇到 `pkg-config --cflags` 返回空：

```bash
# 方式 1：临时允许系统 Cflags（全局生效）
export PKG_CONFIG_ALLOW_SYSTEM_CFLAGS=1
pkg-config --cflags openssl  # 现在有输出了

# 方式 2：根本解决——从 .zshrc 中移除 C_INCLUDE_PATH
unset C_INCLUDE_PATH
unset CPLUS_INCLUDE_PATH
```

### 11.7 相关：尽早构建或安装 pkg-config

**pkg-config 是编译生态的基石工具**。几乎所有 C/C++ 构建系统（autotools、cmake、meson）都依赖 pkg-config 来发现已安装的库。如果 pkg-config 不可用或有 bug，会导致连锁的编译失败。

**鸿蒙系统预装了 pkg-config 0.29.2**（位于 `/data/service/hnp/bin/pkg-config`），一般情况下可以直接使用。但在以下场景中需要自行编译安装：

| 场景 | 说明 |
|------|------|
| 系统预装版本有 bug | 如本文描述的 Cflags 过滤问题（实际是环境变量配置问题，非 pkg-config 本身 bug） |
| 需要更新版本 | 某些新软件的 .pc 文件使用了 pkg-config 新语法 |
| 自定义安装的软件不在系统 PKG_CONFIG_PATH 中 | 需要确保 PKG_CONFIG_PATH 正确设置 |

**如果需要自行编译 pkg-config**，它应作为**第一阶段（基础工具链）的最早编译项之一**，甚至在 sed/coreutils/gawk 之前，因为后续几乎所有软件的 configure 脚本都可能调用 pkg-config 检测依赖。

```bash
# 编译 pkg-config（autotools 项目，依赖很少）
./configure --prefix=$DEFAULT_PREFIX --with-internal-glib
make -j1 && make install

# --with-internal-glib：使用内置 GLib，避免依赖系统 GLib
```

**验证**：
```bash
pkg-config --version
pkg-config --cflags openssl   # 应输出 -I 路径
pkg-config --libs openssl     # 应输出 -L -l 路径
```