---
# 固定元数据头（必须，AI 优先读取）
name: openharmony-compile-guide
description: 鸿蒙系统编译知识库，提供开源软件在鸿蒙系统上编译的完整指南、最佳实践和经验总结
version: 1.1.0
author: OpenHarmony Community
permissions: 文件读写权限、Shell执行权限、网络访问权限（可选，用于获取参考资料）
---

# 鸿蒙系统编译知识库

## 1. Description
本技能是一个完整的鸿蒙系统编译知识库，基于 OpenSSL 和 libffi 在鸿蒙系统上的适配经验整理而成。当用户需要在鸿蒙系统上编译任何开源软件时，可以使用此技能获取：

1. 鸿蒙系统环境特点和配置
2. 编译工具链（Clang + LLVM）的使用方法
3. 预定义宏（__OHOS__）的作用和时机
4. 配置文件继承关系和最佳实践
5. 自动平台检测逻辑的实现方法
6. 常见编译问题的解决方案
7. 与其他平台（Linux/Android/iOS）的对比
8. 不同构建系统的适配策略（Autotools/CMake/自定义Perl等）

这个知识库可以帮助用户快速理解鸿蒙系统的编译环境，避免重复踩坑，提高编译效率。

## 2. When to use
- 用户说："如何在鸿蒙系统上编译 OpenSSL？"
- 用户说："鸿蒙系统用什么编译器？"
- 用户说："鸿蒙系统的 __OHOS__ 宏是什么意思？"
- 用户说："在鸿蒙上编译软件需要设置哪些环境变量？"
- 用户说："鸿蒙系统和 Linux 系统编译有什么区别？"
- 用户说："如何在鸿蒙系统上配置 autotools？"
- 用户说："鸿蒙系统的 clang 预定义了哪些宏？"
- 用户说："编译时找不到 pthread 怎么办？"
- 用户说："鸿蒙系统支持哪些编译工具链？"
- 用户说："为什么鸿蒙系统要用 llvm-ar 而不是 ar？"
- 用户说："如何在配置文件中添加鸿蒙支持？"
- 用户说："鸿蒙系统的动态链接库有什么特点？"
- 用户说："如何在鸿蒙系统上实现自动平台检测？"
- 用户说："编译时提示 __OHOS__ 未定义怎么办？"
- 用户说："鸿蒙系统和 Android 系统的编译环境有什么不同？"
- 用户说："如何在鸿蒙系统上验证编译环境是否正确？"
- 用户说："鸿蒙系统的编译工具链路径在哪里？"
- 用户说："如何在鸿蒙系统上编译其他开源软件？"
- 用户说："鸿蒙系统支持哪些 POSIX 标准？"
- 用户说："如何在鸿蒙系统上配置交叉编译？"
- 用户说："鸿蒙系统的 Makefile 有什么特点？"
- 用户说："如何在鸿蒙系统上调试编译错误？"
- 用户说："如何识别软件使用的构建系统？"
- 用户说："Autotools 和 CMake 在鸿蒙上有什么区别？"
- 用户说："帮我在鸿蒙电脑编译ncurses-6.4"

## 3. How to use

### 3.0 构建系统识别与适配策略

在开始适配之前，首先需要识别软件使用的构建系统，不同的构建系统需要不同的适配策略。

#### 常见构建系统类型

| 构建系统 | 识别特征 | 配置文件 | 适配方式 | 示例 |
|---------|---------|---------|---------|------|
| **Autotools** | 存在 `configure` 脚本 | `configure.ac`, `Makefile.am` | 修改 `config.guess`, `config.sub` | libffi, glib, curl |
| **CMake** | 存在 `CMakeLists.txt` | `CMakeLists.txt`, `*.cmake` | 添加 `CMakeLists.txt` 平台检测 | SQLite, Boost |
| **自定义 Perl** | 存在 `Configure` (大写) | `Configurations/*.conf` | 添加配置文件 + 修改脚本 | OpenSSL |
| **Meson** | 存在 `meson.build` | `meson.build`, `meson_options.txt` | 添加平台检测逻辑 | systemd, gstreamer |
| **Makefile** | 存在 `Makefile` | `Makefile`, `*.mk` | 直接修改 Makefile | 小型项目 |
| **QMake** | 存在 `.pro` 文件 | `*.pro` | 修改 .pro 文件 | Qt 项目 |

#### 构建系统识别命令

```bash
# 检查是否存在 configure (autotools)
if [ -f "configure" ]; then
    echo "检测到 Autotools 构建系统"
fi

# 检查是否存在 CMakeLists.txt
if [ -f "CMakeLists.txt" ]; then
    echo "检测到 CMake 构建系统"
fi

# 检查是否存在 Configure (OpenSSL 风格)
if [ -f "Configure" ] && [ -x "Configure" ]; then
    echo "检测到自定义 Perl Configure 构建系统"
fi

# 检查是否存在 meson.build
if [ -f "meson.build" ]; then
    echo "检测到 Meson 构建系统"
fi

# 检查是否存在 .pro 文件
if ls *.pro 1> /dev/null 2>&1; then
    echo "检测到 QMake 构建系统"
fi
```

#### 不同构建系统的适配要点

**Autotools (configure)**
- 修改 `config.guess` 添加系统检测逻辑
- 修改 `config.sub` 添加操作系统支持
- 生成三元组：`aarch64-unknown-linux-ohos`
- 使用 `--host` 参数指定目标
- **示例**: libffi 3.4.4

**CMake**
- 在 `CMakeLists.txt` 中添加平台检测
- 使用 `CMAKE_SYSTEM_NAME` 变量
- 设置编译器和工具链
- 使用 `-DCMAKE_TOOLCHAIN_FILE` 指定工具链文件

**自定义 Perl Configure (OpenSSL)**
- 添加 `Configurations/*.conf` 配置文件
- 修改 `Configure` 脚本添加自动检测
- 使用目标名称：`openharmony-aarch64`
- 继承 Linux 配置，添加 `__OHOS__` 宏
- **示例**: OpenSSL 1.1.1w

**Meson**
- 在 `meson.build` 中添加平台检测
- 使用 `host_machine.system()` 判断系统
- 设置编译选项和工具链

#### OpenSSL vs libffi 适配对比

| 方面 | OpenSSL (1.1.1w) | libffi (3.4.4) |
|------|------------------|----------------|
| **构建系统** | 自定义 Perl Configure | Autotools (configure) |
| **配置文件** | Configurations/15-openharmony.conf | config.guess, config.sub |
| **平台检测位置** | Configure 脚本 | config.guess 脚本 |
| **检测方式** | Perl 代码 | Shell 脚本 |
| **目标标识** | openharmony-aarch64 | aarch64-unknown-linux-ohos |
| **预定义宏** | __OHOS__ | 无（通过三元组识别） |
| **配置方式** | 目标名称 | 三元组 |
| **继承关系** | linux-generic32.0 | 自动继承 Linux |
| **修改文件数** | 2 个 | 2 个 |
| **补丁大小** | ~2KB | ~1.5KB |

**关键差异总结：**
1. **构建系统不同**：OpenSSL 使用自定义的 Perl Configure 脚本，libffi 使用标准的 autotools
2. **配置方式不同**：OpenSSL 通过目标名称（openharmony-aarch64），libffi 通过三元组（aarch64-unknown-linux-ohos）
3. **检测方式不同**：OpenSSL 在 Configure 脚本中用 Perl 检测，libffi 在 config.guess 中用 Shell 检测
4. **平台标识不同**：OpenSSL 使用 `__OHOS__` 宏，libffi 使用 `linux-ohos` 三元组
5. **文件位置不同**：OpenSSL 需要新建配置文件，libffi 只需修改现有文件

### 3.1 鸿蒙系统环境检查

当用户询问鸿蒙编译相关问题时，首先检查系统环境：

1. 检查系统信息
   - 执行 `uname -s` 查看系统名称（应该显示 HarmonyOS 或 OpenHarmony）
   - 执行 `uname -m` 查看机器架构（aarch64/armv7l/x86_64 等）
   - 执行 `uname -r` 查看内核版本

2. 检查编译器
   - 执行 `which clang` 查看 clang 路径（通常在 /data/service/hnp/bin/clang）
   - 执行 `which clang++` 查看 clang++ 路径
   - 执行 `clang --version` 查看版本信息

3. 检查 LLVM 工具链
   - 执行 `which llvm-ar`（鸿蒙使用 llvm-ar 而不是 GNU ar）
   - 执行 `which llvm-ranlib`
   - 执行 `which llvm-nm`
   - 执行 `which llvm-strip`

4. 检查环境变量
   - 执行 `echo $CC` 查看编译器设置
   - 执行 `echo $CXX` 查看 C++ 编译器设置
   - 执行 `echo $AR` 查看归档工具设置
   - 执行 `echo $RANLIB` 查看 ranlib 设置
   - 执行 `echo $NM` 查看 nm 设置
   - 执行 `echo $STRIP` 查看 strip 设置

5. 检查预定义宏
   - 执行 `clang -dM -E - < /dev/null 2>/dev/null | grep OHOS` 查看鸿蒙相关宏
   - 应该看到 `__OHOS__`, `__OHOS_FAMILY__`, `__OHOS_Major__`

### 3.2 鸿蒙系统编译环境特点

**工具链：**
- 编译器：Clang/Clang++（不是 GCC）
- 工具链：LLVM（llvm-ar, llvm-ranlib, llvm-nm, llvm-strip）
- 汇编器：Perl（通常在 /data/service/hnp/bin/perl）

**预定义宏：**
- `__OHOS__` - OpenHarmony 系统标识（官方标准）
- `__OHOS_FAMILY__` - OpenHarmony 家族标识
- `__OHOS_Major__` - 主版本号
- 注意：这些宏由 Clang 自动定义，无需手动添加

**环境变量：**
- 鸿蒙系统通常会预设置以下环境变量：
  - CC=clang
  - CXX=clang++
  - AR=llvm-ar
  - RANLIB=llvm-ranlib
  - NM=llvm-nm
  - STRIP=llvm-strip

**系统库支持：**
- pthread：线程库支持（直接可用）
- dlfcn：动态链接支持（dlopen/dlsym）
- 标准库：大部分 POSIX 标准库都支持

### 3.3 配置文件最佳实践

**继承关系：**
```
BASE_UNIX
    │
    └── linux-generic32
            │
            └── linux-generic32.0
                    │
                    └── 你的配置（如 openharmony）
                            │
                            ├── aarch64 变体
                            ├── arm 变体
                            └── x86_64 变体
```

**配置示例（以 OpenSSL 为例）：**
```perl
"openharmony" => {
    inherit_from     => [ "linux-generic32.0" ],  # 继承 Linux 配置
    template         => 1,
    cflags           => add("-D__OHOS__"),     # 添加系统宏
    cppflags         => add("-D__OHOS__"),
    cxxflags         => add("-D__OHOS__"),
    bn_ops           => "BN_LLONG RC4_CHAR",
    thread_scheme    => "pthreads",
    dso_scheme       => "dlfcn",
    shared_target    => "linux-shared",
    shared_cflag     => "-fPIC",
    shared_ldflag    => sub { $disabled{pinshared} ? () : "-Wl,-znodelete" },
    shared_extension => ".so.\$(SHLIB_VERSION_NUMBER)",
    enable           => [ "afalgeng" ],
},
```

**关键点：**
1. 继承 `linux-generic32.0` 而不是 `linux-generic32`（带 `.0` 表示 32 位）
2. 添加 `-D__OHOS__` 宏（虽然 Clang 已定义，但显式定义更安全）
3. 使用 `pthreads` 线程方案
4. 使用 `dlfcn` 动态链接方案
5. 使用 `linux-shared` 共享库目标

### 3.4 自动平台检测实现

**OpenSSL Perl Configure 检测逻辑：**
```perl
# 当目标不在目标表中时，自动检测
if (!$table{$target}) {
    # 检测系统信息
    my $sysname = `uname -s 2>/dev/null` || "unknown";
    my $machine = `uname -m 2>/dev/null` || "unknown";
    my $kernel = `uname -r 2>/dev/null` || "unknown";
    
    # 检查是否为 OpenHarmony 系统
    my $is_openharmony = 0;
    if ($sysname =~ m/harmonyos|openharmony/i) {
        $is_openharmony = 1;
    } elsif ($kernel =~ m/harmonyos|openharmony/i) {
        $is_openharmony = 1;
    }
    
    # 如果是 OpenHarmony，映射到对应目标
    if ($is_openharmony) {
        if ($machine =~ m/x86_64/i) {
            $target = "openharmony-x86_64";
        } elsif ($machine =~ m/x86/i) {
            $target = "openharmony-x86";
        } elsif ($machine =~ m/aarch64/i) {
            $target = "openharmony-aarch64";
        } elsif ($machine =~ m/armv[78]/i) {
            $target = "openharmony-arm";
        } elsif ($machine =~ m/riscv64/i) {
            $target = "openharmony-riscv64";
        } else {
            # 默认为 ARM64
            $target = "openharmony-aarch64";
        }
    }
}
```

**libffi config.guess 检测逻辑：**
```bash
# 在 config.guess 中添加
*:HarmonyOS:*)
    case "$UNAME_MACHINE" in
        aarch64|arm64)
            MACHINE=aarch64
            ;;
        armv7*|armv8*)
            MACHINE=arm
            ;;
        x86_64|amd64)
            MACHINE=x86_64
            ;;
        i?86)
            MACHINE=i686
            ;;
        *)
            MACHINE="$UNAME_MACHINE"
            ;;
    esac
    GUESS=${MACHINE}-unknown-linux-ohos
    ;;
```

**关键点：**
1. 检测 `uname -s` 和 `uname -r`（系统名称和内核版本）
2. 使用正则匹配 `harmonyos|openharmony`（不区分大小写）
3. OpenSSL 使用目标名称映射，libffi 使用三元组生成
4. 只在目标不在表中时才检测（避免覆盖用户显式指定的目标）

### 3.5 常见编译问题及解决方案

**问题1：找不到 pthread**
```
错误：undefined reference to 'pthread_create'
原因：未链接 pthread 库
解决：
  1. 检查是否添加了 -lpthread
  2. 鸿蒙系统 pthread 是内置的，通常不需要显式链接
  3. 如果确实需要，添加 LDFLAGS="-lpthread"
```

**问题2：找不到 llvm-ar**
```
错误：ar: command not found
原因：使用了 GNU ar 而不是 LLVM ar
解决：
  1. 使用 AR=llvm-ar
  2. 或确保 /data/service/hnp/bin 在 PATH 中
```

**问题3：__OHOS__ 未定义**
```
错误：error: '__OHOS__' is not defined
原因：代码中使用了 __OHOS__ 宏，但编译器未定义
解决：
  1. Clang 应该自动定义，检查 clang 版本
  2. 手动添加 CFLAGS="-D__OHOS__"
  3. 检查是否在鸿蒙系统上编译
```

**问题4：动态链接错误**
```
错误：undefined reference to 'dlopen'
原因：未链接 dl 库
解决：
  1. 鸿蒙系统支持 dlopen，使用 -ldl
  2. 配置 dso_scheme 为 "dlfcn"
```

**问题5：系统调用不可用**
```
错误：undefined reference to 'syslog'
原因：鸿蒙系统不支持某些系统调用
解决：
  1. 添加 OPENSSL_NO_SYSLOG 宏
  2. 或提供替代实现
```

**问题6：找不到头文件**
```
错误：fatal error: sys/socket.h: No such file
原因：未指定系统头文件路径
解决：
  1. 添加 CPPFLAGS="-I/path/to/sysroot/usr/include"
  2. 或设置 CROSS_SYSROOT 环境变量
```

**问题7：链接错误**
```
错误：undefined reference to 'pthread_create'
原因：未链接 pthread 库
解决：
  1. 添加 LDFLAGS="-L/path/to/sdk/lib"
  2. 确保库路径正确
```

**问题8：汇编代码错误**
```
错误：assembler error: unknown instruction
原因：汇编代码与架构不匹配
解决：
  1. 检查目标架构是否正确
  2. 禁用汇编优化：./configure ... no-asm
```

**问题9: github代码下载慢
```
错误:   wget: connect: Operation timed out 或 
原因：github国内访问网络不稳定
解决：
	1.通过国内镜像站如gitcode、gitee镜像下载，但无法下载release归档包
    2.在github链接前增加 https//ghfast.top/<github原始链接>，提高国内下载速度，wget、git命令均可以使用
```

**问题10：toybox sed 与 autotools 不兼容**
```
错误：子目录 Makefile 中的 top_srcdir 被错误设置为乱码（如 /|）
原因：鸿蒙使用 toybox sed，而非 GNU sed。autotools 生成的 config.status 
      包含复杂的 sed 脚本（多行命令块、分支命令 :t 和 b、条件跳转 t t），
      toybox sed 对这些高级特性的支持可能不完整
解决：
  1. configure 完成后，使用脚本自动修复子目录 Makefile：
     for dir in ncurses include man progs panel menu form test misc c++; do
         if [ -f "$dir/Makefile" ]; then
             perl -pi -e 's/^top_srcdir\s*=.*/top_srcdir\t= ../' "$dir/Makefile"
         fi
     done
  2. 或安装 GNU sed 替代 toybox sed
```

**问题11：临时目录不可写**
```
错误：configure: error: cannot create a temporary directory in /tmp
原因：鸿蒙系统的 /tmp 目录可能不可写或不存在
解决：
  1. 设置 TMPDIR 环境变量指向可写目录：
     export TMPDIR=$HOME/tmp
     mkdir -p $TMPDIR
  2. 在执行 configure 前确保临时目录存在
```

**问题12：Makefile 文件被识别为二进制**
```
错误：grep: Makefile: binary file matches
原因：config.status 生成的 Makefile 可能包含非 ASCII 字符
解决：
  1. 使用 grep -a 强制作为文本处理
  2. 使用 perl -pi -e 进行文本替换
  3. 使用 strings 命令提取可读文本
```

### 3.6 与其他平台对比

**vs Linux：**
| 方面 | Linux | OpenHarmony |
|------|--------|--------------|
| 核心功能 | 100% | 100% ✅ 相同 |
| 编译选项 | 完全相同 | 完全相同 ✅ 继承 |
| 线程支持 | pthreads | pthreads ✅ 相同 |
| 动态链接 | dlfcn | dlfcn ✅ 相同 |
| 系统宏 | 无 | `__OHOS__` ✅ 特有 |
| 编译器 | gcc | clang ⚠️ 不同 |
| sed | GNU sed | toybox sed ⚠️ 功能受限 |
| awk | gawk/mawk | toybox awk ⚠️ 功能受限 |
| shell | bash | mksh/sh ⚠️ 不同 |

**toybox 工具兼容性注意事项：**

| 工具 | GNU 版本 | toybox 版本 | 差异点 |
|------|----------|-------------|--------|
| sed | GNU sed | toybox sed | 不完全支持复杂脚本（多行块、分支命令） |
| awk | gawk/mawk | toybox awk | 功能有限，某些扩展不可用 |
| grep | GNU grep | toybox grep | 基本功能相同 |
| sh | bash | mksh | 语法略有差异 |

**toybox sed 已知问题：**
1. 复杂的多行命令块 `{...}` 处理可能异常
2. 分支命令 `:label` 和 `b`、`t` 跳转可能不完整
3. 某些正则表达式特性不支持
4. 建议对于复杂的 autotools 项目，configure 后检查生成的 Makefile

**解决方案：编译安装 GNU sed**

建议在鸿蒙系统上编译安装 GNU sed 以替代 toybox sed：

```bash
# 编译 GNU sed 4.9
curl -L -o sed-4.9.tar.gz https://ftp.gnu.org/gnu/sed/sed-4.9.tar.gz
tar -xzf sed-4.9.tar.gz && cd sed-4.9
# 应用补丁（参考 build_in_harmonyos/s/sed/4.9/）
./configure --prefix=$HOME/usr/local
make && make install

# 设置 PATH 优先使用 GNU sed
export PATH=$HOME/usr/local/bin:$PATH
```

详细编译指南请参考：`build_in_harmonyos/s/sed/4.9/README.md`

**推荐的 GNU 工具编译列表**

以下 GNU 工具建议在鸿蒙系统上编译安装，以获得更好的兼容性：

| 工具 | 版本 | 用途 | 归档路径 |
|------|------|------|----------|
| GNU sed | 4.9 | 流编辑器，解决 toybox sed 兼容性问题 | s/sed/4.9/ |
| GNU awk | 5.3+ | 文本处理，功能比 toybox awk 更完整 | 待编译 |
| GNU grep | 3.11+ | 文本搜索，功能基本相同 | 待编译 |
| GNU coreutils | 9.4+ | 基础工具集（ls, cp, mv 等） | 待编译 |
| GNU make | 4.4+ | 构建工具，支持更多扩展 | 待编译 |
| GNU bash | 5.2+ | Shell，语法更丰富 | 待编译 |

**vs Android：**
| 方面 | Android | OpenHarmony |
|------|---------|--------------|
| 基础继承 | linux-generic32 | linux-generic32.0 ✅ 相同 |
| 汇编方案 | linux64 | linux64 ✅ 相同 |
| bn_ops | RC4_CHAR | RC4_CHAR ✅ 相同 |
| NDK 检测 | 复杂 | 无 ✅ 简洁 |
| 环境变量 | 动态检测 | 依赖系统 ✅ 简单 |

**vs iOS：**
| 方面 | iOS | OpenHarmony |
|------|-----|--------------|
| 工具链 | Xcode (xcrun) | LLVM (clang) ⚠️ 不同 |
| 汇编方案 | ios64 | linux64 ⚠️ 不同 |
| SDK | iPhoneOS SDK | 系统自带 ⚠️ 不同 |
| 版本限制 | 需要 | 不需要 ✅ 简单 |

### 3.7 Autotools 配置

**三元组格式：**
```
<架构>-<厂商>-<操作系统>
例如：aarch64-unknown-linux-ohos
```

**配置示例：**
```bash
# 使用三元组配置
./configure aarch64-unknown-linux-ohos

# 或使用环境变量
CC=clang CXX=clang++ AR=llvm-ar ./configure
```

**注意：**
- 鸿蒙系统的三元组通常使用 `-unknown-ohos` 作为厂商和操作系统
- 某些构建系统可能需要手动映射三元组到具体目标
- 大多数情况下，直接使用环境变量更简单

### 3.8 验证编译环境

**验证脚本示例：**
```bash
#!/bin/bash
echo "=== 鸿蒙系统编译环境验证 ==="

# 检查系统信息
echo "系统信息:"
echo "  OS: $(uname -s 2>/dev/null || echo 'unknown')"
echo "  Kernel: $(uname -r 2>/dev/null || echo 'unknown')"
echo "  Machine: $(uname -m 2>/dev/null || echo 'unknown')"
echo ""

# 检查编译器
echo "编译器:"
if command -v clang &> /dev/null; then
    echo "  ✓ clang: $(clang --version | head -1)"
else
    echo "  ✗ clang: not found"
fi

if command -v clang++ &> /dev/null; then
    echo "  ✓ clang++: $(clang++ --version | head -1)"
else
    echo "  ✗ clang++: not found"
fi
echo ""

# 检查 LLVM 工具链
echo "LLVM 工具链:"
for tool in llvm-ar llvm-ranlib llvm-nm llvm-strip; do
    if command -v $tool &> /dev/null; then
        echo "  ✓ $tool: found"
    else
        echo "  ✗ $tool: not found"
    fi
done
echo ""

# 检查环境变量
echo "环境变量:"
for var in CC CXX AR RANLIB NM STRIP CFLAGS CXXFLAGS CPPFLAGS LDFLAGS; do
    if [ -n "${!var}" ]; then
        echo "  ✓ $var=${!var}"
    else
        echo "  - $var: (not set)"
    fi
done
echo ""

# 检查 Clang 预定义宏
echo "Clang 预定义宏:"
if command -v clang &> /dev/null; then
    echo "  检查 __OHOS__..."
    if clang -dM -E - < /dev/null 2>/dev/null | grep -q "__OHOS__"; then
        echo "  ✓ __OHOS__: defined"
        clang -dM -E - < /dev/null 2>/dev/null | grep "__OHOS__" | head -5 | sed 's/^/    /  /'
    else
        echo "  ✗ __OHOS__: not defined"
    fi
else
    echo "  ✗ clang not available"
fi
echo ""

# 检查 Perl 模块
echo "Perl 模块:"
if command -v perl &> /dev/null; then
    if perl -MText::Template -e 1 2>/dev/null; then
        echo "  ✓ Text::Template: available"
    else
        echo "  ✗ Text::Template: not available"
    fi
else
    echo "  ✗ perl not available"
fi
echo ""

# 检查线程支持
echo "线程支持:"
if command -v clang &> /dev/null; then
    cat > test_pthread.c << 'EOF'
#include <pthread.h>
int main() {
    pthread_t thread;
    return 0;
}
EOF
    
    if clang test_pthread.c -o test_pthread 2>/dev/null; then
        echo "  ✓ pthread: supported"
        rm -f test_pthread test_pthread.c
    else
        echo "  ✗ pthread: not supported"
        rm -f test_pthread.c
    fi
else
    echo "  ✗ clang not available"
fi
```

### 3.9 知识总结
#### 归档触发时机
- 针对每一次在鸿蒙系统上**首次成功完成构建并测试通过**后，按照以下步骤创建归档：
  - 按照 `<软件名称首字母>/<软件全程>/<版本号>` 创建归档目录
    ```bash
    mkdir -p r/readline/8.2/
    ```
  - 归档结构示例
     ```bash
    build_in_harmonyos/
    ├── SKILL.md
    ├── l/                # l开头命令软件
    │   └── libffi/       # libffi 相关
    │       ├── 3.4.4/
    │       │   ├── README.md
    │       │   └── 0001-port-for-ohos.patch
    │       └── 3.5.2/
    │           ├── README.md
    │           └── 0001-port-for-ohos.patch
    │
    ├── n/                # n开头命令软件
    │   └── ncurses/      # ncurses 相关
    │       └── 6.4/
    │           ├── README.md
    │           └── 0001-port-for-ohos.patch
    │
    ├── o/                # o开头命令软件
    │   └── openssl/      # openssl 相关
    │       └── 1.1.1w/
    │           ├── README.md
    │           └── 0001-support-build-in-harmonyos.patch
    │
    ├── r/                # r开头命令软件
    │   └── readline/     # readline 相关
    │       └── 8.2/
    │           ├── README.md
    │           └── 0001-port-for-ohos.patch
    │
    └── s/                # s开头命令软件
        └── sed/          # GNU sed 相关
            └── 4.9/
                ├── README.md
                └── 0001-port-for-ohos.patch
    ```

#### 补丁命名规范
- **单个补丁**：`0001-port-for-ohos.patch`
- **多个补丁**：`0001-xxx.patch`, `0002-xxx.patch`（按执行顺序编号）
- **命名原则**：
  - 与其他补丁保持一致的 `0001-` 前缀
  - 使用 `0001`, `0002`, `0003`...` 按序编号区分
  - 编号对应补丁的执行顺序
  - 例如：
    - `0001-port-for-ohos.patch`（主要适配补丁）
    - `0002-fix-xxx-bug.patch`（修复某个 bug）
    - `0003-add-xxx-feature.patch`（添加某个功能）

#### 参考对比
   与现有归档对比差异点，便于后续优化类似项目，并提取关键点写入当前的SKILL.md文档


### 3.10 知识提交
** 询问用户是否直接提交知识上库，以用户为准**

## 4. Edge cases

**边缘情况1：交叉编译场景**
- 描述：在 x86_64 主机上编译鸿蒙 ARM64 程序
- 解决：
  1. 需要鸿蒙 NDK 或 sysroot
  2. 设置 CROSS_COMPILE 环境变量
  3. 指定正确的工具链路径

**边缘情况2：不同架构的鸿蒙设备**
- 描述：鸿蒙支持多种架构（ARM64, ARM32, x86_64, RISC-V）
- 解决：
  1. 根据设备架构选择对应的目标
  - aarch64: openharmony-aarch64
  - armv7l: openharmony-arm
  - x86_64: openharmony-x86_64

**边缘情况3：旧版本鸿蒙系统**
- 描述：某些鸿蒙版本可能缺少某些特性
- 解决：
  1. 检查鸿蒙版本号
  2. 添加版本特定的编译选项
  3. 或禁用不支持的特性

**边缘情况4：缺少系统库**
- 描述：某些开源软件依赖的库在鸿蒙上不可用
- 解决：
  1. 查找鸿蒙替代库
  2. 或编译缺失的库
  3. 或禁用相关功能

**边缘情况5：Perl 模块缺失**
- 描述：某些构建系统需要特定的 Perl 模块
- 解决：
  1. OpenSSL 自带 Text::Template 模块在 external/perl/ 目录
  2. 其他软件可能需要手动安装 Perl 模块
  3. 使用 cpan 安装缺失的模块

**边缘情况6：文件系统只读**
- 描述：某些目录（如 /tmp）只读，无法写入临时文件
- 解决：
  1. 使用可写目录（如当前目录）
  2. 或设置 TMPDIR 环境变量指向可写目录
  3. 检查文件权限

**边缘情况7：环境变量冲突**
- 描述：用户设置的环境变量与系统环境冲突
- 解决：
  1. 优先使用系统环境变量
  2. 或明确覆盖系统变量
  3. 检查环境变量优先级

**边缘情况8：编译器版本不兼容**
- 描述：某些软件需要特定版本的 Clang
- 解决：
  1. 检查 Clang 版本（clang --version）
  2. 如果版本过低，考虑升级或使用兼容选项
  3. 或禁用需要新特性的功能

**边缘情况9：多架构同时编译**
- 描述：需要同时编译多个架构的版本（fat binary）
- 解决：
  1. 鸿蒙通常不需要 fat binary
  2. 分别编译每个架构的版本
  3. 使用打包工具合并

**边缘情况10：调试符号问题**
- 描述：调试版本编译时符号处理不当
- 解决：
  1. 使用 -g 选项生成调试符号
  2. 使用 llvm-strip 保留必要符号
  3. 检查 DWARF 版本兼容性

**边缘情况11：Makefile 语法错误**
- 描述：某些 Makefile 使用 GNU Make 扩展，鸿蒙的 make 不支持
- 解决：
  1. 使用标准 Make 语法
  2. 避免使用 GNU Make 特有扩展
  3. 或使用 GNU make

**边缘情况12：路径包含空格**
- 描述：某些路径包含空格，导致解析错误
- 解决：
  1. 使用引号包裹路径
  2. 避免路径中包含空格
  3. 使用转义字符

**边缘情况13：字符编码问题**
- 描述：源文件使用非 UTF-8 编码，导致编译错误
- 解决：
  1. 确保源文件使用 UTF-8 编码
  2. 设置正确的 locale
  3. 转换源文件编码

**边缘情况14：权限问题**
- 描述：某些目录或文件没有读写权限
- 解决：
  1. 检查文件权限（ls -l）
  2. 使用 chmod 修改权限
  3. 或使用 sudo（不推荐）

**边缘情况15：磁盘空间不足**
- 描述：编译过程中磁盘空间不足
- 解决：
  1. 检查磁盘空间（df -h）
  2. 清理临时文件
  3. 或使用更少的并行编译任务

## 5. Implementation

本技能是纯文本描述型技能，无需编写代码。AI 可以通过阅读 SKILL.md 的自然语言描述理解如何使用这些知识。

当用户需要编译相关的帮助时，AI 应该：

1. 首先检查用户是否在鸿蒙系统上（通过 uname 命令）
2. 识别软件使用的构建系统（Autotools/CMake/自定义Perl等）
3. 根据构建系统类型提供相应的适配策略
4. 如果需要，提供环境检查脚本
5. 提供与其他平台的对比，帮助用户理解差异
6. 给出最佳实践建议

## 6. 最佳实践总结

### 6.1 编译前检查清单

在鸿蒙系统上编译任何软件前，建议按以下顺序检查：

1. ✅ 检查系统信息（uname -s, uname -m, uname -r）
2. ✅ 检查编译器（clang, clang++）
3. ✅ 检查 LLVM 工具链（llvm-ar, llvm-ranlib, llvm-nm, llvm-strip）
4. ✅ 检查环境变量（CC, CXX, AR, RANLIB, NM, STRIP）
5. ✅ 检查预定义宏（clang -dM -E | grep OHOS）
6. ✅ 检查 Perl 模块（Text::Template）
7. ✅ 检查线程支持（pthread）
8. ✅ 检查动态链接支持（dlfcn）
9. ✅ **设置临时目录**：`export TMPDIR=$HOME/tmp && mkdir -p $TMPDIR`
10. ✅ **检查工具兼容性**：`sed --version` 确认是 toybox 还是 GNU sed

### 6.2 配置文件编写建议

1. ✅ 继承 linux-generic32.0（32 位）或 linux-generic64（64 位）
2. ✅ 添加 -D__OHOS__ 宏（显式定义更安全）
3. ✅ 使用 pthreads 线程方案
4. ✅ 使用 dlfcn 动态链接方案
5. ✅ 使用 linux-shared 共享库目标
6. ✅ 添加 -fPIC 编译选项
7. ✅ 添加 -Wl,-znodelete 链接选项

### 6.3 编译选项建议

1. ✅ 使用 -O3 优化选项（Release 版本）
2. ✅ 使用 -g 生成调试符号（Debug 版本）
3. ✅ 使用 -Wall 启用所有警告
4. ✅ 使用 -fPIC 生成位置无关代码
5. ✅ 使用 -pthread 启用线程支持
6. ✅ 使用 -std=c++11 指定 C++ 标准

### 6.4 常见错误处理

1. ✅ 找不到头文件：检查 CPPFLAGS 和 sysroot
2. ✅ 找不到库：检查 LDFLAGS 和库路径
3. ✅ 链接错误：检查是否链接了必要的库
4. ✅ 汇编错误：检查目标架构是否正确
5. ✅ 权限错误：检查文件和目录权限
6. ✅ 磁盘空间不足：清理临时文件
7. ✅ **Autotools configure 后处理**：对于复杂项目，检查子目录 Makefile 中的 top_srcdir 变量是否正确

### 6.4.1 Autotools 项目 configure 后处理脚本

对于使用 autotools 构建系统的复杂项目，configure 完成后建议执行以下检查：

```bash
#!/bin/bash
# Autotools 项目 configure 后处理脚本

# 1. 检查子目录 Makefile 中的 top_srcdir 是否正确
for makefile in $(find . -name Makefile -not -path "./.git/*"); do
    dir=$(dirname "$makefile")
    top_srcdir=$(grep -a "^top_srcdir" "$makefile" 2>/dev/null | head -1)
    
    if [ -n "$top_srcdir" ]; then
        # 检查 top_srcdir 是否包含乱码
        if echo "$top_srcdir" | grep -q '[^[:print:]]'; then
            echo "警告: $makefile 中的 top_srcdir 包含乱码"
            echo "  原值: $(echo "$top_srcdir" | cat -v)"
            
            # 计算正确的相对路径
            depth=$(echo "$dir" | tr -cd '/' | wc -c)
            correct_top_srcdir=$(printf '%0.s../' $(seq 1 $depth))
            correct_top_srcdir=${correct_top_srcdir%/}  # 移除末尾斜杠
            
            echo "  修复为: top_srcdir = $correct_top_srcdir"
            perl -pi -e "s/^top_srcdir\s*=.*/top_srcdir\\t= $correct_top_srcdir/" "$makefile"
        fi
    fi
done

# 2. 验证 config.h 是否生成
if [ -f "config.h" ]; then
    echo "✓ config.h 已生成"
else
    echo "✗ config.h 未生成，请检查 configure 输出"
fi

# 3. 检查临时目录设置
echo "临时目录: ${TMPDIR:-/tmp}"
if [ ! -d "${TMPDIR:-/tmp}" ]; then
    echo "警告: 临时目录不存在，请设置 TMPDIR"
fi
```

### 6.5 调试技巧

1. ✅ 使用 -v 或 --verbose 查看详细编译过程
2. ✅ 使用 --dry-run 测试配置不实际编译
3. ✅ 使用 --debug 生成调试版本
4. ✅ 查看编译日志排查问题
5. ✅ 使用 strace 跟踪系统调用（如果可用）

### 6.6 修改文件技巧
**修改文件的标准化流程（7 步）**
#### 6.6.1. 预处理：提取文件的 “可锚定修改区域”  
  首先需要从目标文件中提取唯一、稳定的代码片段（锚点），而非依赖行号。锚点的选择原则：
  - 用函数 / 类定义、注释标记、唯一变量名 作为锚点（避免用空行、通用注释）；
  - 提取锚点前后的上下文（通常 ±3 行），确保定位的是 “唯一区域”。
  
  实操命令（AI/agent 执行）：
  ```bash
  # 示例：定位Python文件中calculate_total函数的定义（锚点）
  # 1. 查找锚点行（返回锚点所在行号，仅用于辅助，不用于硬编码修改）
  ANCHOR_LINE=$(grep -n -A 3 -B 1 "def calculate_total(prices: list\[float\], discount: float) -> float:" target_file.py | head -1 | cut -d: -f1)
  # 2. 提取锚点上下文（保存为临时文件，便于分析修改）
  sed -n "$((ANCHOR_LINE-1)),$((ANCHOR_LINE+10))p" target_file.py > ~/tmp/target_snippet.txt
  ```
  - 关键：`grep`用精确的代码特征（如完整函数签名）定位，而非行号；
  - 提取上下文时，范围稍大（如 ±10 行），确保包含整个待修改区域。

#### 6.6.2.基于锚点片段生成 “原子化修改指令”
  不直接修改原文件，而是基于提取的~/tmp/target_snippet.txt，生成 **“按内容替换” 的指令 **（而非 “在第 X 行插入 / 删除”），核心要求：
  - 生成的修改指令必须是“旧内容 → 新内容” 的映射（原子化替换）；
  - 旧内容必须是原文件中唯一存在的片段（避免全局替换出错）。
  
  示例修改指令（标准化格式）：
  ```bash
  # 【修改类型】：替换代码块
  # 【旧内容】（必须精确匹配原文件）：
  OLD_CONTENT='def calculate_total(prices: list[float], discount: float) -> float:
      """计算总价（未考虑折扣上限）"""
      total = sum(prices) * (1 - discount)
      return total'

  # 【新内容】（包含修改后的完整代码）：
  NEW_CONTENT='def calculate_total(prices: list[float], discount: float) -> float:
      """计算总价（限制折扣上限为30%）"""
      if not prices:
          raise ValueError("价格列表不能为空")
      max_discount = min(discount, 0.3)
      total = sum(prices) * (1 - max_discount)
      return total'

  # 【执行命令】（用sed按内容替换，而非行号）：
  # 注意：sed的分隔符用|避免/转义，-z将文件作为单行处理（匹配多行内容）
  sed -z "s|$OLD_CONTENT|$NEW_CONTENT|g" target_file.py > ~/tmp/modified_file.py
  ```
#### 6.6.3.执行修改：写入临时文件（避免直接修改原文件）
  执行上述生成的sed命令，将修改后的内容写入临时文件（如~/tmp/modified_file.py），而非直接覆盖原文件。
  - 核心原则：所有修改先落地到临时文件，验证通过后再替换原文件；
  - 兼容处理：如果是 “插入代码”（而非替换），则基于锚点定位插入位置：
  ```bash
  # 示例：在锚点行后插入代码（用sed的a命令，基于锚点内容而非行号）
  sed "/def calculate_total(/a \    # 新增：折扣上限校验" target_file.py > ~/tmp/modified_file.py
  ```
#### 6.6.4.校验 1：语法/格式合法性检查
  先验证临时文件的基础合法性，避免语法错误：
  ```bash
  # 按语言选择校验工具（示例为Python）
  if ! python -m py_compile ~/tmp/modified_file.py; then
      echo "语法错误：修改后的文件无法编译"
      exit 1  # 终止流程，反馈错误
  fi

  # 代码风格检查（可选，确保符合规范）
  pylint --disable=all --enable=E ~/tmp/modified_file.py  # 只检查错误（E类），忽略警告
  ```

#### 6.6.5.校验 2：内容精准性验证
  验证临时文件中是否包含预期的修改内容，且未篡改其他区域：
  ```bash
  # 1. 检查新内容是否正确写入
  if ! grep -q "max_discount = min(discount, 0.3)" ~/tmp/modified_file.py; then
      echo "修改失败：未找到折扣上限逻辑"
      exit 1
  fi

  # 2. 检查原文件的其他核心内容未被篡改（示例：检查其他函数是否存在）
  if ! grep -q "def calculate_tax(total: float) -> float" ~/tmp/modified_file.py; then
      echo "修改异常：其他函数被意外删除"
      exit 1
  fi
  ```

#### 6.6.6.校验 3：业务逻辑验证（可选，关键代码必做）
  如果修改涉及业务逻辑，AI/agent 执行预设的测试用例，验证修改后的代码逻辑正确：
  ```bash
  # 示例：运行单元测试验证修改后的函数
  python -c "
  from ~/tmp/modified_file import calculate_total
  try:
      assert calculate_total([100,200], 0.4) == 210.0
      assert calculate_total([], 0.2) raises ValueError
      print('逻辑验证通过')
  except AssertionError:
      print('逻辑验证失败：结果不符合预期')
      exit 1
  "
  ```
#### 6.6.7：替换原文件：原子化覆盖（避免文件损坏）
  所有校验通过后，用临时文件原子化替换原文件（避免中途中断导致文件损坏）：
  ```bash
  # 1. 备份原文件（保留修改记录）
  cp target_file.py target_file.py.bak.$(date +%Y%m%d%H%M%S)

  # 2. 原子化替换（mv命令是原子操作，避免文件写入中断）
  mv ~/tmp/modified_file.py target_file.py

  # 3. 清理临时文件
  rm -f ~/tmp/target_snippet.txt
  ```

#### 关键避坑技巧（解决行号漂移核心问题）
  1. 禁用 “行号硬编码”，全程用 “内容锚点”
      - ❌ 错误做法：sed -i '10s/old/new/' target.py（行号 10 可能因之前的修改变化）；
      - ✅ 正确做法：sed -z "s|old_content|new_content|g" target.py（基于内容匹配，不受行号影响）。

  2. 多行替换用-z参数（sed）

      `sed`默认按行处理，多行替换需用`-z`将文件视为单行（用NULL分隔），避免换行符导致匹配失败：
      ```bash
      # 多行替换示例（关键：用|作为分隔符，避免/转义）
      sed -z "s|def calculate_total(.*) -> float:
      \"\"\"计算总价（未考虑折扣上限）\"\"\"
      total = sum(prices) * (1 - discount)
      return total|def calculate_total(.*) -> float:
      \"\"\"计算总价（限制折扣上限为30%）\"\"\"
      if not prices:
          raise ValueError(\"价格列表不能为空\")
      max_discount = min(discount, 0.3)
      total = sum(prices) * (1 - max_discount)
      return total|g" target.py > ~/tmp/modified.py
      ```

  3. 复杂修改用 awk（替代 sed）

      如果修改涉及 “条件判断 + 多行处理”，用`awk`更灵活，同样基于内容锚点：
      ```bash
      # 示例：awk定位函数并修改
      awk '
      # 匹配锚点，开始处理
      /def calculate_total\(/ {
          print $0  # 打印锚点行
          getline; print $0  # 打印注释行
          # 插入新的校验逻辑
          print "    if not prices:"
          print "        raise ValueError(\"价格列表不能为空\")"
          print "    max_discount = min(discount, 0.3)"
          getline; # 跳过原total行
          print "    total = sum(prices) * (1 - max_discount)"  # 替换原逻辑
          next  # 跳过后续处理
      }
      # 其他行原样输出
      1
      ' target_file.py > /tmp/modified_file.py
      ```

#### 完整流程示例（端到端）
  假设要修改order.py中的calculate_total函数，完整的执行流程，以脚本的行程呈现如下，可供指令参考：
  ```bash
  #!/bin/bash
  # 步骤1：提取锚点上下文
  ANCHOR_PATTERN="def calculate_total(prices: list\[float\], discount: float) -> float:"
  grep -q "$ANCHOR_PATTERN" order.py || { echo "锚点不存在，终止修改"; exit 1; }

  # 步骤2：生成修改指令（AI输出）
  OLD_CONTENT='def calculate_total(prices: list[float], discount: float) -> float:
      """计算总价（未考虑折扣上限）"""
      total = sum(prices) * (1 - discount)
      return total'
  NEW_CONTENT='def calculate_total(prices: list[float], discount: float) -> float:
      """计算总价（限制折扣上限为30%）"""
      if not prices:
          raise ValueError("价格列表不能为空")
      max_discount = min(discount, 0.3)
      total = sum(prices) * (1 - max_discount)
      return total'

  # 步骤3：执行修改（写入临时文件）
  sed -z "s|$OLD_CONTENT|$NEW_CONTENT|g" order.py > ~/tmp/modified_order.py

  # 步骤4：语法校验
  if ! python -m py_compile /tmp/modified_order.py; then
      echo "语法错误，修改失败"
      exit 1
  fi

  # 步骤5：内容校验
  if ! grep -q "max_discount = min(discount, 0.3)" ~/tmp/modified_order.py; then
      echo "修改未生效，内容缺失"
      exit 1
  fi

  # 步骤6：逻辑校验
  python -c "
  from /tmp/modified_order import calculate_total
  try:
      assert calculate_total([100,200], 0.4) == 210.0
      calculate_total([], 0.2)
  except ValueError as e:
      assert str(e) == '价格列表不能为空'
  except AssertionError:
      print('逻辑验证失败')
      exit 1
  " || exit 1

  # 步骤7：替换原文件
  cp order.py order.py.bak.$(date +%Y%m%d%H%M%S)
  mv /tmp/modified_order.py order.py
  echo "修改成功，原文件已备份"
  ```

### 6.7 补丁技巧
  生成补丁的流程
  1. 复制备份原文件
  2. 按照规划的方案修改文件
  3. 验证是否修改成功
  4. 确保所有需要修改的文件均得到修改
  5. 通过diff -Naur 进行补丁生成，多个文件可以通过列表方式如下
  ```bash
  diff -Naur \
  project_old/src/main.c project_new/src/main.c \
  project_old/include/config.h project_new/include/config.h \
  > my_patch.patch
  ```
  6. 应用补丁文件，确保补丁生效后与原目标修改相同

### 6.8 Autotools系列构建系统修改技巧
  1. 了解config.guess 的核心目的
    - 生成系统三元组（triplet），格式为：<架构>-<厂商>-<操作系统>│
    - 例如：aarch64-unknown-linux-ohos
  2. 了解config.guess 的实现方式
    不同版本可能有不同的实现方式：
    - 通过 GUESS 变量赋值：GUESS=${MACHINE}-unknown-linux-ohos
    - 通过 echo 直接打印：echo "aarch64-unknown-linux-ohos"
    - 通过 return 退出：echo "aarch64-unknown-linux-ohos"; exit
  3. 了解config.sub 的核心目的
    - 验证和规范化三元组
    - 将三元组分解为：CPU、厂商、操作系统、内核等组件
  4. 修改原则
    1. 最小化修改：只修改必要的部分，避免影响其他功能
    2. 保持兼容性：确保修改不会破坏原有功能
    3. 遵循规范：遵循 autotools 的规范和惯例
  5. 根据这些信息，详细分析对应工程中的文件，确定修改方案进行修改

## 7. 参考资料

- OpenSSL 官方文档：https://www.openssl.org/docs/
- libffi 官方文档：https://github.com/libffi/libffi
- OpenHarmony 官方网站：https://www.openharmony.cn/
- HarmonyOS 开发者文档：https://developer.huawei.com/consumer/cn/doc/
- Clang 文档：https://clang.llvm.org/docs/
- LLVM 文档：https://llvm.org/docs/
- Autotools 文档：https://www.gnu.org/software/autoconf/
- CMake 文档：https://cmake.org/documentation/
- POSIX 标准：https://pubs.opengroup.org/onlinepubs/9699919699/

## 8. License

本技能遵循 MIT 许可证，可自由使用和修改。
