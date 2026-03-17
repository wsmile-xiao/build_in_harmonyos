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
- 用户说："辛迪，来一下"

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

**问题14：fstat() 对管道/终端返回 EACCES**
```
错误：cat: standard output: Permission denied
      fstat(STDOUT_FILENO) failed: errno=13, Permission denied
原因：鸿蒙系统安全机制限制，对管道、终端、套接字的文件描述符调用 fstat() 返回 EACCES
影响：
  - GNU cat、head、tail 等调用 fstat(stdin/stdout) 的命令会失败
  - write() 系统调用正常（数据可以正常写入）
  - 只有 fstat() 被限制（无法获取文件描述符的元信息）
排查：
  # 验证 fstat 对 stdout 的行为
  $ cat > test_fstat.c << 'EOF'
  #include <sys/stat.h>
  #include <stdio.h>
  #include <errno.h>
  #include <string.h>
  int main() {
      struct stat st;
      if (fstat(STDOUT_FILENO, &st) < 0) {
          printf("fstat failed: errno=%d, %s\n", errno, strerror(errno));
          return 1;
      }
      printf("fstat succeeded\n");
      return 0;
  }
  EOF
  $ clang test_fstat.c -o test_fstat
  $ ./test_fstat          # 终端输出：fstat failed: errno=13, Permission denied
  $ ./test_fstat > /tmp/out.txt  # 文件输出：fstat succeeded
解决：
  1. 使用 __OHOS__ 宏进行条件编译
  2. 当 fstat() 返回 EACCES 或 EPERM 时，使用默认值：
     - st_blksize = 4096 (默认 I/O 块大小)
     - st_mode = S_IFIFO (视为管道)
  3. 参考：build_in_harmonyos/c/coreutils/9.10/0002-fix-fstat-for-harmonyos.patch
代码示例：
  #ifdef __OHOS__
  static inline int
  ohos_fstat_compat (int fd, struct stat *st)
  {
    if (fstat (fd, st) == 0)
      return 0;
    if (errno == EACCES || errno == EPERM)
      {
        memset (st, 0, sizeof (*st));
        st->st_blksize = 4096;
        st->st_mode = S_IFIFO;
        return 0;
      }
    return -1;
  }
  #define OHOS_FSTAT(fd, st) ohos_fstat_compat ((fd), (st))
  #else
  #define OHOS_FSTAT(fd, st) fstat ((fd), (st))
  #endif
```

**问题15：github代码下载慢**
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

**问题13：toybox expr 复合正则表达式 Bug**
```
错误：config.status 生成的 Makefile 包含乱码，或 sed 进程卡住
原因：toybox expr 在处理复合正则表达式（使用 \| 操作符）时存在严重 bug，
      会输出乱码或导致进程异常
排查过程：
  1. 使用 ps 找到卡住的进程
  2. 查看 /proc/<pid>/cmdline 获取完整命令
  3. 分析命令中变量的来源
  4. 使用 bash -x 追踪 config.status 执行
  5. 定位到 expr 命令输出异常
  6. 对比 toybox expr 和 GNU expr 的行为
验证命令：
  # toybox expr (错误)
  expr X"ncurses/Makefile" : 'X\(.*[^/]\)//*[^/][^/]*/*$' \| . : '\(.\)'
  # 输出: 乱码
  
  # GNU expr (正确)
  gexpr X"ncurses/Makefile" : 'X\(.*[^/]\)//*[^/][^/]*/*$' \| . : '\(.\)'
  # 输出: ncurses
解决：
  1. 编译安装 GNU coreutils（包含 GNU expr）
  2. 设置 PATH 优先使用 GNU 工具
  3. 详细指南参考：build_in_harmonyos/c/coreutils/9.10/README.md
影响范围：
  - 所有使用 autotools 的项目
  - config.status 使用复杂 expr 命令提取路径
```

### 3.6 鸿蒙 musl libc 与 Linux glibc 差异

鸿蒙系统使用 **musl libc** 而非 Linux 常用的 **glibc**，这种差异会导致某些软件在编译时出现问题。

#### 3.6.1 核心差异对比

| 特性 | glibc | musl libc (鸿蒙) | 影响 |
|------|-------|------------------|------|
| FILE 结构体 | 暴露内部字段（`_IO_read_ptr` 等） | **不透明类型**，内部结构不可访问 | gnulib stdio 扩展模块需要适配 |
| `__freadahead` 函数 | 有 | 无 | 无法直接获取预读数据量 |
| `__freadptr` 函数 | 有 | 无 | 无法直接获取缓冲区指针 |
| stdio_ext.h | 提供完整的扩展函数 | 仅提供 `__fwriting`、`__freading` 等 | 功能受限 |
| 线程局部存储 | 完整支持 | 支持但有差异 | 某些多线程代码需适配 |
| 动态链接 | ld-linux.so | ld-musl-*.so | 加载器不同 |

#### 3.6.2 FILE 结构体差异详解

**glibc 的 FILE 结构（可访问内部字段）：**
```c
struct _IO_FILE {
  int _flags;           /* 标志位 */
  char* _IO_read_ptr;   /* 当前读取位置 ✅ 可访问 */
  char* _IO_read_end;   /* 读取缓冲区结束 ✅ 可访问 */
  char* _IO_read_base;  /* 读取缓冲区起始 ✅ 可访问 */
  char* _IO_write_base; /* 写入缓冲区起始 ✅ 可访问 */
  char* _IO_write_ptr;  /* 当前写入位置 ✅ 可访问 */
  char* _IO_write_end;  /* 写入缓冲区结束 ✅ 可访问 */
  // ... 更多字段
};
```

**musl 的 FILE 结构（不透明类型）：**
```c
// musl 中 FILE 是不透明指针
typedef struct _IO_FILE FILE;
// 内部结构对用户代码不可见 ❌ 无法访问任何内部字段
```

#### 3.6.3 gnulib stdio 扩展模块适配

gnulib 提供了三个 stdio 扩展模块，用于直接操作 FILE 结构的内部缓冲区：

| 模块 | 功能 | glibc 实现 | musl 适配方案 |
|------|------|------------|---------------|
| `freadahead.c` | 获取预读数据量 | 访问 `_IO_read_end - _IO_read_ptr` | 返回 0（安全回退） |
| `freadptr.c` | 获取读取缓冲区指针 | 返回 `_IO_read_ptr` | 返回 NULL（调用者回退到标准 API） |
| `freadseek.c` | 移动读取指针 | 修改 `_IO_read_ptr` | abort()（理论上不会执行） |

**适配代码示例（freadahead.c）：**
```c
#elif defined __OHOS__ || (defined __linux__ && !defined __GLIBC__)
  /* HarmonyOS uses musl libc with opaque FILE structure.
     musl provides __fwriting in <stdio_ext.h> to check write mode.
     For musl without __freadahead, we use a safe fallback.  */
# include <stdio_ext.h>
  if (__fwriting (fp))
    return 0;
  /* musl's FILE is opaque; we cannot access internal buffers directly.
     Return 0 as a safe fallback - this means we don't report pending input.
     This is correct for most use cases since musl handles buffering internally.  */
  return 0;
```

**适配原则：**
1. 使用 musl 提供的公开 API（如 `__fwriting`）
2. 无法实现的功能使用安全回退（返回 0 或 NULL）
3. 回退后调用者会使用标准 API（如 fread、fgetc）
4. 这是 GNU 代码中的标准兼容模式

#### 3.6.4 检测 musl 的方法

**编译时检测：**
```c
#if defined(__linux__) && !defined(__GLIBC__)
  // musl libc 环境
#endif

#if defined(__OHOS__)
  // HarmonyOS（使用 musl）
#endif
```

**运行时检测：**
```bash
# 检查 C 库类型
ldd /bin/sh | grep libc
# glibc: libc.so.6
# musl:  ld-musl-aarch64.so.1

# 或检查可执行文件
file /bin/sh
# glibc: dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2
# musl:  dynamically linked, interpreter /lib/ld-musl-aarch64.so.1
```

#### 3.6.5 常见 musl 兼容性问题

**问题1：gnulib 假设 glibc 的 FILE 结构**
```
错误：error: incomplete definition of type 'struct _IO_FILE'
原因：代码尝试访问 FILE 的内部字段，但 musl 的 FILE 是不透明类型
解决：
  1. 添加条件编译检测 musl
  2. 使用公开 API 或安全回退
  3. 参考 GNU coreutils 9.10 的适配方案
```

**问题2：缺少 glibc 特有函数**
```
错误：undefined reference to '__xmknod' 或 '__fxstat'
原因：这些是 glibc 的内部函数，musl 不提供
解决：
  1. 检查是否有替代 API
  2. 使用条件编译禁用相关功能
  3. 提供兼容性封装
```

**问题3：线程局部存储差异**
```
错误：thread-local storage 相关错误
原因：musl 的 TLS 实现与 glibc 略有差异
解决：
  1. 使用标准的 __thread 或 _Thread_local
  2. 避免使用 glibc 特有的 TLS 扩展
```

#### 3.6.6 参考项目

已完成 musl 适配的项目：
- **GNU coreutils 9.10**: `build_in_harmonyos/c/coreutils/9.10/README.md`
- 包含 freadahead.c、freadptr.c、freadseek.c 的完整适配方案

### 3.7 鸿蒙系统特有的系统调用限制

鸿蒙系统出于安全考虑，对某些 POSIX 系统调用有特殊限制。在移植软件时需要注意这些差异。

#### 3.7.1 fstat() 对管道/终端的限制

**限制描述：**

| 文件描述符类型 | fstat() 结果 | write() 结果 | 说明 |
|---------------|-------------|--------------|------|
| 普通文件 | ✅ 成功 | ✅ 成功 | 正常 |
| 管道 (pipe) | ❌ EACCES | ✅ 成功 | 可以写入，但无法获取元信息 |
| 终端 (tty) | ❌ EACCES | ✅ 成功 | 可以输出，但无法获取元信息 |
| 套接字 (socket) | ❌ EACCES | ✅ 成功 | 可以通信，但无法获取元信息 |

**受影响的软件：**

- GNU coreutils: cat, head, tail, dd, split, tee 等
- 其他调用 `fstat(STDIN_FILENO)` 或 `fstat(STDOUT_FILENO)` 的软件

**解决方案模板：**

```c
/* harmonyos-fstat-compat.h */
#ifndef HARMONYOS_FSTAT_COMPAT_H
#define HARMONYOS_FSTAT_COMPAT_H

#include <errno.h>
#include <sys/stat.h>
#include <string.h>

#ifdef __OHOS__

static inline int
ohos_fstat_compat (int fd, struct stat *st)
{
  if (fstat (fd, st) == 0)
    return 0;

  if (errno == EACCES || errno == EPERM)
    {
      /* HarmonyOS returns EACCES for pipes/terminals/sockets */
      memset (st, 0, sizeof (*st));
      st->st_blksize = 4096;      /* Default I/O block size */
      st->st_mode = S_IFIFO;      /* Treat as pipe/FIFO */
      return 0;
    }

  return -1;
}

#define OHOS_FSTAT(fd, st) ohos_fstat_compat ((fd), (st))

#else /* !__OHOS__ */

#define OHOS_FSTAT(fd, st) fstat ((fd), (st))

#endif /* __OHOS__ */

#endif /* HARMONYOS_FSTAT_COMPAT_H */
```

**使用方法：**

```c
#include "harmonyos-fstat-compat.h"

/* 替换 fstat 调用 */
if (OHOS_FSTAT (STDOUT_FILENO, &st) < 0)
  error (EXIT_FAILURE, errno, "standard output");
```

**验证 __OHOS__ 宏：**

```bash
# 检查编译器预定义的宏
clang -dM -E - < /dev/null | grep OHOS
# 输出:
# #define __OHOS__ 1
# #define __OHOS_FAMILY__ 1
# #define __OHOS_Major__ 0
```

#### 3.7.2 fstat() 和 lseek() 对管道/终端的限制

**限制描述：**

HarmonyOS 出于安全考虑，对管道、终端、套接字的文件描述符禁止 `fstat()` 和 `lseek()` 系统调用。

| 系统调用 | 普通文件 | 管道 | 终端 | Socket | 说明 |
|----------|----------|------|------|--------|------|
| fstat() | ✅ 成功 | ❌ EACCES | ❌ EACCES | ❌ EACCES | 无法获取元信息 |
| lseek() | ✅ 成功 | ❌ EACCES | ❌ EACCES | ❌ EACCES | 无法移动位置 |
| write() | ✅ 成功 | ✅ 成功 | ✅ 成功 | ✅ 成功 | 数据写入正常 |
| read() | ✅ 成功 | ✅ 成功 | ✅ 成功 | ✅ 成功 | 数据读取正常 |

**受影响的软件：**

- GNU coreutils: cat, dd, head, sort, split, tail 等
- 其他调用 `fstat(stdin/stdout)` 或 `lseek()` 的软件

**解决方案模板：**

```c
/* fstat 兼容性处理 */
if (fstat (STDOUT_FILENO, &st) < 0)
  {
# ifdef __OHOS__
    /* HarmonyOS returns EACCES for pipes/terminals/sockets. */
    if (errno == EACCES || errno == EPERM)
      {
        memset (&st, 0, sizeof st);
        st.st_blksize = 4096;      /* 默认 I/O 块大小 */
        st.st_mode = S_IFIFO;      /* 视为管道 */
      }
    else
# endif
      error (EXIT_FAILURE, errno, "standard output");
  }

/* lseek 兼容性处理 */
off_t pos = lseek (fd, offset, SEEK_CUR);
if (pos < 0)
  {
# ifdef __OHOS__
    /* HarmonyOS returns EACCES for lseek on pipes/terminals.
       This is expected behavior, not an error. */
    if (errno == EACCES || errno == EPERM || errno == ESPIPE)
      return -1;  /* 静默返回失败 */
# endif
    error (0, errno, "lseek failed");
  }
```

**验证 __OHOS__ 宏：**

```bash
clang -dM -E - < /dev/null | grep OHOS
# 输出:
# #define __OHOS__ 1
# #define __OHOS_FAMILY__ 1
```

**参考实现：**

- toybox 不调用 fstat(stdin/stdout)，使用固定缓冲区 4096 字节
- 完整补丁参考：`build_in_harmonyos/c/coreutils/9.10/0002-fix-fstat-for-harmonyos.patch`

**典型案例：wc 命令输出格式问题**

这是一个隐蔽的逻辑 bug，值得详细分析。

**问题现象：**

`wc` 命令从管道读取时，输出格式不对齐：

```
# 期望输出（制表符分隔，宽度7）
$ echo "" | wc
      0       0       0

# 实际输出（空格分隔，宽度1）
$ echo "" | wc
0 0 0
```

**根因分析：**

问题出在 `compute_number_width()` 函数：

```c
static int
compute_number_width (idx_t nfiles, struct fstatus const *fstatus)
{
  int width = 1;

  if (0 < nfiles && fstatus[0].failed <= 0)  // 关键条件
    {
      int minimum_width = 1;
      // ...
      for (idx_t i = 0; i < nfiles; i++)
        if (! fstatus[i].failed)  // 这里检查 failed == 0
          {
            // 设置 minimum_width 的逻辑
          }
      // ...
    }
  return width;
}
```

**逻辑陷阱：**

1. 从管道读取时，`nfiles == 1`（stdin_only 模式）
2. `fstat(STDIN_FILENO, ...)` 失败，返回 `-1`
3. `fstatus[0].failed = -1`
4. 条件 `fstatus[0].failed <= 0` 为 **真**（-1 <= 0），进入第一个分支
5. 但 `!fstatus[0].failed` 为 **假**（!(-1) = 0），for 循环内不执行
6. `minimum_width` 保持为 1，导致输出格式错误

**关键点：** `failed <= 0` 和 `!failed` 是两个不同的条件！

- `failed <= 0`：包含 `failed == 0`（成功）和 `failed == -1`（失败）
- `!failed`：仅 `failed == 0`（成功）

**解决方案：**

在 for 循环中添加对失败情况的处理：

```c
for (idx_t i = 0; i < nfiles; i++)
  if (! fstatus[i].failed)
    {
      // ... 原有逻辑
    }
#ifdef __OHOS__
  else if (fstatus[i].failed < 0)
    {
      /* HarmonyOS: fstat failed on pipe/special file (returns EACCES).
         Use default width 7 for proper alignment in output. */
      minimum_width = 7;
    }
#endif
```

**经验总结：**

1. **条件判断要精确**：`<= 0` 和 `== 0` 含义不同，需要仔细区分
2. **多文件测试用例**：管道输入和文件输入的行为可能不同
3. **检查所有分支**：不仅要检查成功路径，也要处理失败路径
4. **参考：** `build_in_harmonyos/c/coreutils/9.10/README.md`

#### 3.7.3 SELinux 策略对软链接的限制（重要）

**根本原因：**

HarmonyOS 的 SELinux 策略限制了用户进程对软链接的访问。这不是内核不支持，而是安全策略限制。

| 系统/工具 | SELinux 上下文 | readlink/lstat |
|-----------|----------------|----------------|
| toybox | `u:object_r:toybox_exec:s0` | ✅ 成功 |
| 用户程序 | `u:object_r:hmdfs:s0` | ❌ EACCES |

**受影响的系统调用：**

| 系统调用 | 普通文件 | 软链接（用户进程） | 说明 |
|----------|----------|-------------------|------|
| lstat() | ✅ 成功 | ❌ EACCES | SELinux 策略限制 |
| stat() | ✅ 成功 | ❌ EACCES | SELinux 策略限制 |
| readlink() | ✅ 成功 | ❌ EACCES | SELinux 策略限制 |
| readlinkat() | ✅ 成功 | ❌ EACCES | SELinux 策略限制 |

**受影响的 GNU coreutils 命令：**

| 命令 | toybox | GNU coreutils | 原因 |
|------|--------|---------------|------|
| ls | ✅ | ❌ | lstat 获取链接属性 |
| stat | ✅ | ❌ | lstat 获取链接状态 |
| rm | ✅ | ❌ | lstat 检查文件类型 |
| cp | ✅ | ❌ | lstat 检查是否为链接 |
| mv | ✅ | ❌ | lstat 检查源文件 |
| chmod | ✅ | ❌ | lstat 获取文件状态 |
| chown | ✅ | ❌ | lstat 获取文件状态 |
| readlink | ✅ | ❌ | readlink 系统调用受限 |

**正常工作的命令：**

| 命令 | toybox | GNU coreutils | 说明 |
|------|--------|---------------|------|
| touch | ✅ | ✅ | 不需要 lstat |
| cat | ✅ | ✅ | 通过 O_PATH 打开链接后读取目标 |
| du | ✅ | ✅ | 跟随链接 |
| realpath | ✅ | ❌ | 内部使用 readlink |
| file | ✅ | ✅ | 使用其他方式检测 |
| find | ✅ | ✅ | 使用 readdir 获取 d_type |

**解决方案：**

对于涉及软链接的操作，使用 toybox 命令作为兜底：

```bash
# 在 .zshrc 或脚本中添加别名
alias ls='/bin/ls'
alias rm='/bin/rm'
alias cp='/bin/cp'
alias mv='/bin/mv'
alias stat='/bin/stat'
alias chmod='/bin/chmod'
alias chown='/bin/chown'
alias readlink='/bin/readlink'

# 或者按需使用完整路径
/bin/rm -f some_symlink
/bin/ls -la directory_with_symlinks
```

**注意事项：**

1. `ln -s` 本身可以创建软链接，但创建的链接文件可能无法被 GNU 工具正常访问
2. `ln -sf`（强制覆盖）有额外问题：会创建带随机后缀的乱码文件
3. 清理损坏的软链接必须使用 toybox 的 `rm`
4. **SELinux 限制无法在用户空间代码中绕过**，必须使用具有正确上下文的系统工具

**toybox ln -sf 的特殊问题：**

```bash
# 正常创建
ln -s source.txt link        # 创建: link -> source.txt ✓

# 强制覆盖问题
ln -sf source.txt link       # 创建: link_GdinNM -> source.txt ✗ (随机后缀)
```

建议在鸿蒙系统上避免使用 `ln -sf`，改用：
```bash
rm -f link && ln -s source.txt link
```

**为 GNU coreutils 设置 SELinux 上下文（需要 root 权限）：**

```bash
# 设置 SELinux 上下文（如果需要）
chcon u:object_r:toybox_exec:s0 $HOME/usr/local/bin/ls
chcon u:object_r:toybox_exec:s0 $HOME/usr/local/bin/rm
# ... 对其他命令执行相同操作
```

#### 3.7.4 /tmp 目录只读

**限制描述：**
- `/tmp` 以 erofs（只读文件系统）挂载
- 无法在此目录创建临时文件

**解决方案：**
```bash
# 设置 TMPDIR 环境变量
export TMPDIR=$HOME/tmp
mkdir -p $TMPDIR
```

#### 3.7.5 toybox 工具功能限制

**限制描述：**
- toybox expr 不支持复合正则表达式（`\|` 操作符）
- toybox sed 对复杂脚本支持不完整
- toybox awk 功能有限

**解决方案：**
编译安装 GNU 工具替代（详见 build_in_harmonyos/c/coreutils/9.10/）

#### 3.7.6 鸿蒙系统改进建议

以下问题建议鸿蒙系统开发者关注和改进：

**1. SELinux 策略优化**

| 问题 | 当前状态 | 建议改进 |
|------|----------|----------|
| 用户进程无法访问软链接 | SELinux 返回 EACCES | 放宽 `hmdfs` 域对 symlink 的访问权限 |
| 缺少策略切换机制 | 无 | 提供开发者模式，允许自定义 SELinux 策略 |

**建议理由**：
- 软链接是 Unix/Linux 系统的基本功能
- 用户编译的 GNU 工具无法正常处理软链接，影响开发体验
- 其他 Unix-like 系统没有此限制

**2. 文件系统改进**

| 问题 | 当前状态 | 建议改进 |
|------|----------|----------|
| `/tmp` 只读 | erofs 挂载 | 默认提供可写临时目录 |
| `fstat()` 对管道返回 EACCES | 特殊行为 | 返回合理的默认值或 ENOTSUP |

**3. 系统调用一致性**

| 系统调用 | 当前行为 | 建议行为 |
|----------|----------|----------|
| `fstat(pipe_fd)` | EACCES | 返回管道的 stat 结构（mode=S_IFIFO） |
| `lseek(pipe_fd)` | EACCES | 返回 ESPIPE（标准行为） |
| `lstat(symlink)` | EACCES | 返回软链接的 stat 结构 |

**4. 开发者体验改进**

| 方面 | 建议改进 |
|------|----------|
| 包管理 | 提供官方 GNU coreutils 包 |
| 文档 | 记录系统调用差异和限制 |
| 调试 | 提供更详细的错误信息（如 SELinux 拒绝原因） |

**5. toybox 功能增强**

| 命令 | 问题 | 建议 |
|------|------|------|
| expr | 不支持 `\|` 复合正则 | 实现完整 POSIX expr |
| sed | 复杂脚本支持不完整 | 增强 GNU 兼容性 |
| ln -sf | 创建带随机后缀的文件 | 修复 `-f` 强制覆盖逻辑 |

### 3.8 与其他平台对比

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

| 工具 | 版本 | 用途 | 归档路径 | 优先级 |
|------|------|------|----------|--------|
| GNU coreutils | 9.10 | 基础工具集，**修复 toybox expr bug** | c/coreutils/9.10/ | ⭐⭐⭐ 必须 |
| GNU sed | 4.9 | 流编辑器，解决 toybox sed 兼容性问题 | s/sed/4.9/ | ⭐⭐⭐ 必须 |
| GNU awk | 5.3+ | 文本处理，功能比 toybox awk 更完整 | 待编译 | ⭐⭐ 推荐 |
| GNU grep | 3.11+ | 文本搜索，功能基本相同 | 待编译 | ⭐ 可选 |
| GNU make | 4.4+ | 构建工具，支持更多扩展 | 待编译 | ⭐ 可选 |
| GNU bash | 5.2+ | Shell，语法更丰富 | 待编译 | ⭐ 可选 |

**编译顺序建议**：
1. GNU coreutils（提供 expr，最关键）
2. GNU sed（替代 toybox sed）
3. 其他工具（按需安装）

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

### 3.9 Autotools 配置

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

### 3.10 验证编译环境

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

### 3.11 知识总结
#### 归档触发时机
- 针对每一次在鸿蒙系统上**首次成功完成构建并测试通过**后，按照以下规范创建归档：
#### 归档目录及命名规范
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

### 3.12 测试失败分析经验

在鸿蒙系统上运行测试套时，需要正确区分失败原因，避免将系统限制误判为软件问题。

#### 测试失败分类

| 失败原因 | 特征 | 示例 | 是否需修复 |
|----------|------|------|-----------|
| **系统权限限制** | 错误信息含 "Operation not permitted" 或 "Permission denied" | 硬链接创建、符号链接创建、fifo 创建 | ❌ 系统限制 |
| **系统能力缺失** | 跳过原因明确指出缺失能力 | inotify、/dev/full、SELinux 支持 | ❌ 系统限制 |
| **代码逻辑问题** | 输出与期望不匹配，非权限原因 | wc 输出格式、错误消息格式 | ✅ 需要修复 |
| **toybox 命令混用** | 测试使用了系统 PATH 中的 toybox 命令 | expr 正则表达式、sed 复杂脚本 | ⚠️ 检查 PATH |

#### 检查方法

**1. 检查测试使用的命令版本**

```bash
# 查看测试日志中的 PATH 设置
grep "PATH=" tests/test-suite.log | head -5

# 确认使用的是编译后的版本
which expr sed ls rm
# 应该输出: $HOME/usr/local/bin/expr

# 检查版本
expr --version  # 应该是 GNU coreutils
sed --version   # 应该是 GNU sed
```

**2. 分析错误信息**

```bash
# 提取所有失败测试的错误信息
grep -E "Operation not permitted|Permission denied" tests/test-suite.log | sort -u

# 统计各类错误
grep -c "Operation not permitted" tests/test-suite.log
grep -c "Permission denied" tests/test-suite.log
grep -c "hard link\|symlink\|fifo" tests/test-suite.log
```

**3. 区分权限限制与逻辑问题**

```bash
# 权限限制示例（无需修复）
ln: failed to create hard link 'a-ctime' => 'a': Operation not permitted
ln: failed to create symbolic link 'symlink': Permission denied
mkfifo: cannot create fifo 'fifo': Operation not permitted

# 逻辑问题示例（需要修复）
# wc 输出格式问题
--- exp
+++ out
@@ -1 +1 @@
-      0       0       0
+ 0 0 0
```

#### 测试套执行注意事项

**1. 首次运行确认弹窗**

鸿蒙系统对首次运行的新编译二进制会弹窗确认，这可能导致：
- 测试超时
- 时间敏感测试失败
- help-version 测试失败

**建议做法：**

```bash
# 在运行 make check 前，先手动执行一次各命令
cd src
for cmd in cat dd head sort split tail wc; do
    ./$cmd --version > /dev/null  # 触发确认弹窗
done
cd ..

# 或者在运行测试时注意确认弹窗
make check
```

**2. make check 是否重新编译**

`make check` 会重新编译修改过的源文件。如果修改了源码，需要：
- 确保修改已保存
- 重新编译后再运行测试
- 新编译的二进制首次运行仍需确认

**3. 测试环境变量检查**

```bash
# 确认环境变量正确加载
source $HOME/.zshrc
echo $TMPDIR      # 应为 $HOME/tmp
echo $PATH        # $HOME/usr/local/bin 应在前面
```

#### 常见测试失败处理

**情况1：硬链接/符号链接创建失败**

```
ln: failed to create hard link: Operation not permitted
```

**判断：** 鸿蒙系统安全限制，无需修复。

**情况2：测试使用了 toybox 命令**

**检查方法：**

```bash
# 查看测试日志中的命令版本
grep -E "toybox|GNU coreutils" tests/test-suite.log | head -10

# 如果看到 toybox 版本信息，说明 PATH 设置有问题
```

**解决：** 确保 `$HOME/usr/local/bin` 在 PATH 最前面。

**情况3：输出格式或行为差异**

需要仔细分析是否是代码逻辑问题：
1. 对比期望输出和实际输出
2. 分析差异原因
3. 参考 wc 案例的分析方法

### 3.13 知识提交
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
11. ✅ **执行代码扫描**：检测已知的兼容性问题模式

### 6.1.1 编译前代码扫描

在编译前扫描源码，提前发现 HarmonyOS 兼容性问题，避免反复编译测试。

#### 扫描目标

**HarmonyOS 已知限制相关的代码模式：**

| 问题类型 | 扫描模式 | 影响范围 |
|----------|----------|----------|
| fstat 对管道限制 | `fstat.*STDIN_FILENO\|fstat.*STDOUT_FILENO\|fstat.*STDERR_FILENO` | cat, dd, head, sort, split, tail 等 |
| lseek 对管道限制 | `lseek.*SEEK_CUR\|lseek.*SEEK_SET` | head 等 |
| /tmp 只读 | `"/tmp"\|/tmp/` | 需使用 $TMPDIR |
| musl FILE 结构差异 | `_IO_.*_ptr\|_IO_.*_base\|__fbufsize` | gnulib stdio 扩展 |

#### 扫描脚本

```bash
#!/bin/bash
# harmonyos_precompile_scan.sh - 编译前兼容性扫描

PROJECT_DIR="$1"
ISSUES=0

echo "=== HarmonyOS 兼容性扫描 ==="
echo "扫描目录: $PROJECT_DIR"
echo ""

# 1. 扫描 fstat 对 stdin/stdout/stderr 的调用
echo "1. 检查 fstat(stdin/stdout/stderr) 调用..."
FOUND=$(grep -rn "fstat.*STDIN_FILENO\|fstat.*STDOUT_FILENO\|fstat.*STDERR_FILENO" "$PROJECT_DIR/src" 2>/dev/null | grep -v "\.o:" | wc -l)
if [ "$FOUND" -gt 0 ]; then
    echo "   ⚠️  发现 $FOUND 处可能受 fstat 限制影响的代码"
    grep -rn "fstat.*STDIN_FILENO\|fstat.*STDOUT_FILENO\|fstat.*STDERR_FILENO" "$PROJECT_DIR/src" 2>/dev/null | grep -v "\.o:" | head -10
    ISSUES=$((ISSUES + FOUND))
else
    echo "   ✅ 未发现 fstat(stdin/stdout/stderr) 调用"
fi

# 2. 扫描 lseek 调用
echo ""
echo "2. 检查 lseek 调用..."
FOUND=$(grep -rn "lseek.*SEEK_CUR\|lseek.*SEEK_SET" "$PROJECT_DIR/src" 2>/dev/null | grep -v "\.o:" | wc -l)
if [ "$FOUND" -gt 0 ]; then
    echo "   ⚠️  发现 $FOUND 处可能受 lseek 限制影响的代码"
    grep -rn "lseek.*SEEK_CUR\|lseek.*SEEK_SET" "$PROJECT_DIR/src" 2>/dev/null | grep -v "\.o:" | head -10
    ISSUES=$((ISSUES + FOUND))
else
    echo "   ✅ 未发现 lseek 调用"
fi

# 3. 扫描 /tmp 硬编码路径
echo ""
echo "3. 检查 /tmp 硬编码路径..."
FOUND=$(grep -rn '"/tmp"' "$PROJECT_DIR/src" 2>/dev/null | grep -v "\.o:" | wc -l)
if [ "$FOUND" -gt 0 ]; then
    echo "   ⚠️  发现 $FOUND 处 /tmp 硬编码路径（应使用 $TMPDIR）"
    grep -rn '"/tmp"' "$PROJECT_DIR/src" 2>/dev/null | grep -v "\.o:" | head -10
    ISSUES=$((ISSUES + FOUND))
else
    echo "   ✅ 未发现 /tmp 硬编码路径"
fi

# 4. 扫描 glibc 特有的 FILE 结构访问
echo ""
echo "4. 检查 glibc FILE 结构访问..."
FOUND=$(grep -rn "_IO_.*_ptr\|_IO_.*_base\|__fbufsize\|fp->_IO" "$PROJECT_DIR/lib" "$PROJECT_DIR/src" 2>/dev/null | grep -v "\.o:" | wc -l)
if [ "$FOUND" -gt 0 ]; then
    echo "   ⚠️  发现 $FOUND 处 glibc FILE 结构访问（musl 不兼容）"
    grep -rn "_IO_.*_ptr\|_IO_.*_base\|__fbufsize\|fp->_IO" "$PROJECT_DIR/lib" "$PROJECT_DIR/src" 2>/dev/null | grep -v "\.o:" | head -10
    ISSUES=$((ISSUES + FOUND))
else
    echo "   ✅ 未发现 glibc FILE 结构访问"
fi

# 5. 扫描 stat 对 stdin/stdout 的调用
echo ""
echo "5. 检查 stat(\"-\") 调用（stdin/stdout 特殊处理）..."
FOUND=$(grep -rn 'stat.*"-"\|streq.*"-".*stat' "$PROJECT_DIR/src" 2>/dev/null | grep -v "\.o:" | wc -l)
if [ "$FOUND" -gt 0 ]; then
    echo "   ⚠️  发现 $FOUND 处可能受 stat 限制影响的代码"
    grep -rn 'stat.*"-"\|streq.*"-".*stat' "$PROJECT_DIR/src" 2>/dev/null | grep -v "\.o:" | head -10
    ISSUES=$((ISSUES + FOUND))
else
    echo "   ✅ 未发现 stat(\"-\") 调用"
fi

echo ""
echo "=== 扫描结果 ==="
if [ "$ISSUES" -gt 0 ]; then
    echo "发现 $ISSUES 处潜在问题，建议提前适配后再编译"
    echo ""
    echo "适配方法参考："
    echo "  - fstat/lseek: 参考 SKILL.md 3.7.2 节"
    echo "  - musl FILE: 参考 SKILL.md 3.6 节"
    echo "  - /tmp: 使用 getenv(\"TMPDIR\") 替代"
    exit 1
else
    echo "✅ 未发现已知兼容性问题"
    exit 0
fi
```

#### 使用方法

```bash
# 解压源码后，编译前执行扫描
tar -xf project-x.y.z.tar.xz
cd project-x.y.z

# 执行扫描
/path/to/harmonyos_precompile_scan.sh .

# 如果发现问题，先适配再编译
# 适配完成后重新扫描确认
```

#### 扫描结果处理流程

```
┌─────────────────┐
│  解压源码        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  执行代码扫描    │◄──────────────────┐
└────────┬────────┘                    │
         │                             │
    发现问题?                           │
    ┌────┴────┐                        │
    │是       │否                      │
    ▼         ▼                        │
┌─────────┐  ┌─────────┐               │
│ 分析适配 │  │ 执行编译 │               │
└────┬────┘  └─────────┘               │
     │                                 │
     ▼                                 │
┌─────────┐                            │
│重新扫描 ├────────────────────────────┘
└─────────┘
```

#### 常见扫描结果及适配优先级

| 问题类型 | 优先级 | 适配难度 | 说明 |
|----------|--------|----------|------|
| fstat(stdin/stdout) | 高 | 中 | 直接导致命令失败 |
| lseek 对管道 | 高 | 中 | 直接导致命令失败 |
| musl FILE 结构 | 高 | 高 | 编译错误或运行时崩溃 |
| /tmp 硬编码 | 中 | 低 | 影响临时文件功能 |
| stat("-") | 中 | 中 | 影响 stdin/stdout 处理 |

### 6.2 环境变量配置建议

为了让系统优先使用用户编译安装的工具和库，建议在 `~/.zshrc` 中添加以下配置：

```bash
# 将用户安装的工具优先放到 PATH 前面
export PATH=$HOME/usr/local/bin:$HOME/.local/bin:$PATH

# 设置 pkg-config 搜索路径
export PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig

# 设置头文件搜索路径
export C_INCLUDE_PATH=$HOME/usr/local/include:$C_INCLUDE_PATH
export CPLUS_INCLUDE_PATH=$HOME/usr/local/include:$CPLUS_INCLUDE_PATH

# 设置库文件搜索路径
export LIBRARY_PATH=$HOME/usr/local/lib:$LIBRARY_PATH
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
```

**⚠️ 重要：编译环境工具链依赖**

在编译软件前，**必须确保 PATH 中优先使用已修复的 GNU 工具**。这是因为：

1. **构建过程中的工具链调用**：make、configure 等会调用 sed、sort、awk 等工具
2. **管道操作**：这些工具通过管道通信，需要修复 fstat 问题
3. **鸡生蛋问题**：需要先有修复的工具，才能编译其他软件

**正确的编译流程：**

```bash
# 1. 先编译并安装基础工具（sed, coreutils）
# 2. 设置 PATH 使用修复的工具
export PATH=$HOME/usr/local/bin:$PATH

# 3. 验证工具可用
sed --version    # 应该是 GNU sed
sort --version   # 应该是 GNU coreutils

# 4. 然后再编译其他软件
./configure && make && make install
```

**配置说明：**

| 环境变量 | 用途 | 说明 |
|----------|------|------|
| `PATH` | 可执行程序搜索路径 | 将 `$HOME/usr/local/bin` 放在前面，优先使用 GNU sed 等工具 |
| `PKG_CONFIG_PATH` | pkg-config 搜索路径 | 让 configure 能找到已安装库的 .pc 文件 |
| `C_INCLUDE_PATH` | C 头文件搜索路径 | 编译时能找到已安装库的头文件 |
| `CPLUS_INCLUDE_PATH` | C++ 头文件搜索路径 | C++ 编译时能找到已安装库的头文件 |
| `LIBRARY_PATH` | 静态库搜索路径 | 链接时能找到已安装的静态库 |
| `LD_LIBRARY_PATH` | 动态库搜索路径 | 运行时能找到已安装的动态库 |

**生效方式：**

```bash
# 修改后重新加载配置
source ~/.zshrc

# 或重新打开终端
```

**问题16：make install-man 失败 "Can't open perl script"**

**现象：**
```bash
make install-man
# 错误: Can't open perl script "man/help2man": Permission denied
```

**根因分析：**

这个错误信息是**误导性的**！真正的原因是：

```
help2man (Perl 脚本)
    │
    └─ 内部调用 sed 处理文本
        │
        └─ sed 遇到管道 fstat 问题 ❌
```

**解决方案：**

```bash
# 使用修复后的 GNU sed
export PATH=$HOME/usr/local/bin:$PATH

# 然后执行 make
make install-man
```

**关于 help2man：**

| 方面 | 说明 |
|------|------|
| 是什么 | GNU 独立软件包，Perl 脚本 |
| 需要编译吗 | 不需要，是纯 Perl 脚本 |
| 需要修改 shebang 吗 | **不需要**！help2man.PL 是自解压脚本，自动嵌入正确的 perl 路径 |
| 依赖什么 | Perl + sed（需修复 fstat）|

**重要提示：** help2man.PL 是自解压脚本，会自动检测并嵌入正确的 perl 路径。

**help2man 安装方法：**

```bash
# 下载解压后直接安装
cd help2man-1.49.3
perl help2man.PL --stdout > $HOME/usr/local/bin/help2man
chmod +x $HOME/usr/local/bin/help2man

# 首次运行需点击确认（鸿蒙安全机制）
help2man --version
```

详细文档：`build_in_harmonyos/h/help2man/1.49.3/README.md`

### 6.3 配置文件编写建议

1. ✅ 继承 linux-generic32.0（32 位）或 linux-generic64（64 位）
2. ✅ 添加 -D__OHOS__ 宏（显式定义更安全）
3. ✅ 使用 pthreads 线程方案
4. ✅ 使用 dlfcn 动态链接方案
5. ✅ 使用 linux-shared 共享库目标
6. ✅ 添加 -fPIC 编译选项
7. ✅ 添加 -Wl,-znodelete 链接选项

### 6.4 编译选项建议

1. ✅ 使用 -O3 优化选项（Release 版本）
2. ✅ 使用 -g 生成调试符号（Debug 版本）
3. ✅ 使用 -Wall 启用所有警告
4. ✅ 使用 -fPIC 生成位置无关代码
5. ✅ 使用 -pthread 启用线程支持
6. ✅ 使用 -std=c++11 指定 C++ 标准

### 6.5 常见错误处理

1. ✅ 找不到头文件：检查 CPPFLAGS 和 sysroot
2. ✅ 找不到库：检查 LDFLAGS 和库路径
3. ✅ 链接错误：检查是否链接了必要的库
4. ✅ 汇编错误：检查目标架构是否正确
5. ✅ 权限错误：检查文件和目录权限
6. ✅ 磁盘空间不足：清理临时文件
7. ✅ **Autotools configure 后处理**：对于复杂项目，检查子目录 Makefile 中的 top_srcdir 变量是否正确

### 6.6 补丁开发与验证最佳实践

#### 6.6.1 三目录法

进行补丁开发时，推荐使用"三目录法"来管理代码：

```
project-x.y.z-orig/     # 原始源码（只读，用于对比和重新打补丁）
project-x.y.z-work/     # 工作目录（修改代码，开发补丁）
project-x.y.z-test/     # 测试目录（验证补丁是否正确应用）
```

**工作流程：**

```bash
# 1. 解压并创建目录
tar -xf project-x.y.z.tar.xz
mv project-x.y.z project-x.y.z-orig
cp -a project-x.y.z-orig project-x.y.z-work

# 2. 在 work 目录开发修改
cd project-x.y.z-work
# ... 进行修改 ...

# 3. 生成补丁（使用 -U 参数扩大上下文）
diff -U 10 ../project-x.y.z-orig/src/foo.c src/foo.c > ../fix-xxx.patch

# 4. 验证补丁
cp -a ../project-x.y.z-orig ../project-x.y.z-test
cd ../project-x.y.z-test
patch -p1 < ../fix-xxx.patch
```

#### 6.6.2 补丁生成规范

**使用 `diff -U N` 扩大上下文范围：**

```bash
# 默认上下文 3 行（可能因相似代码导致错位）
diff -u orig/file.c work/file.c > patch.diff

# 推荐上下文 10 行（避免相似代码混淆）
diff -U 10 orig/file.c work/file.c > patch.diff
```

| 参数 | 上下文行数 | 适用场景 |
|------|------------|----------|
| `-u` (默认) | 3 行 | 简单修改，代码唯一性强 |
| `-U 5` | 5 行 | 中等复杂度修改 |
| `-U 10` | 10 行 | 复杂修改，或代码有相似片段 |
| `-U 15` | 15 行 | 非常复杂修改，确保定位准确 |

**补丁文件格式：**

```diff
From: OpenHarmony Developer <developer@openharmony.io>
Subject: [PATCH] 简短描述补丁目的

--- project-orig/src/file.c
+++ project-work/src/file.c
@@ -行号,长度 +行号,长度 @@
 上下文代码（10行）
-删除的行
+新增的行
 上下文代码（10行）
```

#### 6.6.3 补丁验证流程

```bash
# 1. 创建干净的测试目录
rm -rf project-x.y.z-test
cp -a project-x.y.z-orig project-x.y.z-test

# 2. 应用补丁
cd project-x.y.z-test
patch -p1 < ../fix-xxx.patch

# 3. 检查应用结果
# 应该看到: patching src/file.c
# 不应该看到: Hunk #1 FAILED at xxx

# 4. 验证编译
./configure --prefix=$HOME/usr/local
make

# 5. 验证功能
# 运行相关测试
```

**常见补丁问题及解决：**

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `Hunk #1 FAILED` | 上下文不匹配 | 使用 `-U 10` 扩大上下文 |
| `patch unexpectedly ends` | 补丁文件损坏 | 重新生成补丁 |
| `Reversed (or previously applied)` | 补丁已应用 | 恢复原始文件后重试 |
| `can't find file to patch` | 路径不正确 | 检查 `-p` 参数或路径 |

#### 6.6.4 HarmonyOS 特有问题快速排查

**排查 fstat/lseek 问题：**

```bash
# 检查命令是否受 fstat/lseek 限制影响
echo "test" | cat 2>&1    # 正常应该输出 "test"
echo "test" | dd 2>&1     # 正常应该输出 "test"
echo "a\nb\nc" | sort 2>&1  # 正常应该排序输出

# 如果看到 "Permission denied" 或 "stat failed" 错误，
# 说明该命令需要修复 fstat 调用
```

**受影响的典型命令：**

| 命令 | 问题类型 | 典型错误信息 |
|------|----------|-------------|
| cat | fstat | `standard output: Permission denied` |
| dd | fstat | `standard input: Permission denied` |
| head | fstat, lseek | `cannot seek to relative offset` |
| sort | fstat | `stat failed: -: Permission denied` |
| split | fstat | `standard input: Permission denied` |
| tail | fstat | `cannot fstat` |

**快速定位代码位置：**

```bash
# 在源码中搜索可能受影响的调用
grep -rn "fstat.*STDIN_FILENO\|fstat.*STDOUT_FILENO" src/
grep -rn "lseek.*SEEK_CUR\|lseek.*SEEK_SET" src/
```

**验证 __OHOS__ 宏可用：**

```bash
clang -dM -E - < /dev/null | grep OHOS
# 预期输出:
# #define __OHOS__ 1
# #define __OHOS_FAMILY__ 1
```

### 6.5.1 Autotools 项目 configure 后处理脚本

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

### 6.6 调试技巧

1. ✅ 使用 -v 或 --verbose 查看详细编译过程
2. ✅ 使用 --dry-run 测试配置不实际编译
3. ✅ 使用 --debug 生成调试版本
4. ✅ 查看编译日志排查问题
5. ✅ 使用 strace 跟踪系统调用（如果可用）

### 6.7 修改文件技巧
**修改文件的标准化流程（7 步）**
#### 6.7.1. 预处理：提取文件的 “可锚定修改区域”  
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

#### 6.7.2.基于锚点片段生成 “原子化修改指令”
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
#### 6.7.3.执行修改：写入临时文件（避免直接修改原文件）
  执行上述生成的sed命令，将修改后的内容写入临时文件（如~/tmp/modified_file.py），而非直接覆盖原文件。
  - 核心原则：所有修改先落地到临时文件，验证通过后再替换原文件；
  - 兼容处理：如果是 “插入代码”（而非替换），则基于锚点定位插入位置：
  ```bash
  # 示例：在锚点行后插入代码（用sed的a命令，基于锚点内容而非行号）
  sed "/def calculate_total(/a \    # 新增：折扣上限校验" target_file.py > ~/tmp/modified_file.py
  ```
#### 6.7.4.校验 1：语法/格式合法性检查
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

#### 6.7.5.校验 2：内容精准性验证
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

#### 6.7.6.校验 3：业务逻辑验证（可选，关键代码必做）
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
#### 6.7.7：替换原文件：原子化覆盖（避免文件损坏）
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

### 6.8 补丁生成最佳实践

#### 6.8.1 标准流程（三目录法）

**问题背景**：直接编写补丁文件容易出错，行号、上下文不匹配会导致补丁无法应用。

**推荐方法**：使用三个独立的目录进行补丁生成和验证。

```bash
# 步骤1：创建原始备份目录（从 tar 包解压，永不修改）
tar -xzf package-1.0.tar.gz
mv package-1.0 package-1.0-orig

# 步骤2：创建工作目录（在此修改和验证）
cp -a package-1.0-orig package-1.0-work
cd package-1.0-work

# 步骤3：在工作目录中修改文件
# ... 执行修改操作 ...

# 步骤4：验证修改是否正确（编译测试）
./configure && make

# 步骤5：生成补丁
cd ..
diff -u package-1.0-orig/file1.c package-1.0-work/file1.c > 0001-fix.patch
diff -u package-1.0-orig/file2.c package-1.0-work/file2.c >> 0001-fix.patch
# 或使用循环处理多个文件：
# for f in $(find package-1.0-work -name "*.c" -type f); do
#     orig="${f/work/orig}"
#     diff -u "$orig" "$f" >> 0001-fix.patch
# done

# 步骤6：创建验证目录（验证补丁可正确应用）
cp -a package-1.0-orig package-1.0-verify
cd package-1.0-verify
patch -p1 < ../0001-fix.patch

# 步骤7：验证补丁后能否正常编译
./configure && make

# 步骤8：确认无误后清理
rm -rf package-1.0-verify
```

#### 6.8.2 目录命名规范

| 目录类型 | 命名 | 用途 | 修改权限 |
|----------|------|------|----------|
| 原始备份 | `package-1.0-orig` | 保存原始代码，用于 diff | ❌ 禁止修改 |
| 工作目录 | `package-1.0-work` | 修改和验证代码 | ✅ 可以修改 |
| 验证目录 | `package-1.0-verify` | 验证补丁正确性 | 仅应用补丁 |

#### 6.8.3 常见错误及避免方法

**错误1：直接修改 tar 包解压的目录**
```
❌ 错误做法：
tar -xzf package.tar.gz
cd package
# 直接修改...
diff -u package.orig package > patch  # package.orig 不存在！

✅ 正确做法：
tar -xzf package.tar.gz
mv package package-orig          # 先重命名
cp -a package-orig package-work  # 再复制工作目录
```

**错误2：在工作目录中生成补丁后继续修改**
```
❌ 错误做法：
cd package-work
# 修改文件...
diff -u ../package-orig/file.c file.c > patch
# 继续修改...
diff -u ../package-orig/file.c file.c >> patch  # 补丁包含旧内容！

✅ 正确做法：
cd package-work
# 修改文件...
# 验证编译...
# 确认所有修改完成后，一次性生成补丁
diff -u ../package-orig/file.c file.c > patch
# 不再修改工作目录
```

**错误3：补丁生成后删除工作目录**
```
❌ 错误做法：
diff -u orig/file.c work/file.c > patch
rm -rf work  # 工作目录删除，无法重新生成补丁

✅ 正确做法：
# 保留工作目录，直到补丁验证通过
diff -u orig/file.c work/file.c > patch
cp -a orig verify
cd verify && patch -p1 < ../patch && make  # 验证
# 验证通过后可清理
```

**错误4：使用错误的 diff 参数**
```
❌ 错误做法：
diff file1.c file2.c > patch      # 缺少 -u 参数，上下文不足
diff -u a/file.c b/file.c > patch # 路径不标准

✅ 正确做法：
diff -u package-orig/src/file.c package-work/src/file.c > patch
# 路径应以目录名为前缀，方便 patch -p1 应用
```

#### 6.8.4 补丁验证清单

在生成补丁后，必须验证：

1. ✅ 补丁能正确应用（`patch -p1 --dry-run < patch`）
2. ✅ 应用后的文件与工作目录一致（`diff -r orig work`）
3. ✅ 应用后能正常编译
4. ✅ 补丁文件格式正确（有 `---` 和 `+++` 行）

#### 6.8.5 多文件补丁生成脚本

```bash
#!/bin/bash
# generate-patch.sh - 自动生成多文件补丁

ORIG_DIR="package-1.0-orig"
WORK_DIR="package-1.0-work"
PATCH_FILE="0001-port-for-ohos.patch"

# 清空补丁文件
> "$PATCH_FILE"

# 查找所有修改过的文件
for work_file in $(find "$WORK_DIR" -type f \( -name "*.c" -o -name "*.h" -o -name "*.sh" \)); do
    orig_file="${work_file/$WORK_DIR/$ORIG_DIR}"
    
    if [ -f "$orig_file" ]; then
        if ! diff -q "$orig_file" "$work_file" > /dev/null 2>&1; then
            echo "添加修改: $work_file"
            diff -u "$orig_file" "$work_file" >> "$PATCH_FILE"
        fi
    fi
done

echo "补丁生成完成: $PATCH_FILE"
echo "补丁行数: $(wc -l < "$PATCH_FILE")"
```

### 6.9 Autotools系列构建系统修改技巧
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

### 6.10 问题排查方法论

在鸿蒙系统上编译软件时，可能会遇到各种问题。本节总结了系统化的问题排查方法。

#### 6.10.1 进程卡住问题排查

**场景**：configure 或 make 过程中进程卡住，无响应。

**排查步骤**：

```bash
# 步骤1：找到卡住的进程
ps aux | grep -E "configure|make|sed|expr"

# 步骤2：查看进程详细信息
cat /proc/<pid>/cmdline | tr '\0' ' ' | head -c 500
cat /proc/<pid>/stack  # 查看调用栈

# 步骤3：检查进程状态
cat /proc/<pid>/status | grep -E "State|Threads"

# 步骤4：如果命令很长，保存到文件
cat /proc/<pid>/cmdline | tr '\0' ' ' > /tmp/cmd.txt

# 步骤5：分析命令，确定卡住的具体位置
# 检查命令中的变量值、管道操作等

# 步骤6：手动执行相关命令验证
# 例如，单独执行 sed 或 expr 命令测试
```

**常见原因**：
- toybox 工具与 GNU 工具不兼容
- 复杂的 shell 脚本语法差异
- 死循环或无限等待

#### 6.10.2 乱码/二进制数据问题排查

**场景**：生成的文件包含乱码或被识别为二进制文件。

**排查步骤**：

```bash
# 步骤1：检查文件类型
file Makefile

# 步骤2：查看文件十六进制内容
hexdump -C Makefile | head -20

# 步骤3：查找非 ASCII 字符
hexdump -C Makefile | grep -E "[^[:print:]]" | head -10

# 步骤4：检查 NULL 字节
grep -c $'\x00' Makefile

# 步骤5：强制作为文本处理
grep -a "pattern" Makefile
```

**常见原因**：
- toybox 工具 bug（如 expr 复合正则表达式）
- 终端转义序列被错误写入文件
- 变量展开异常

#### 6.10.3 变量污染排查

**场景**：shell 变量包含意外的值或乱码。

**排查步骤**：

```bash
# 步骤1：使用 bash -x 追踪脚本执行
bash -x ./config.status --file=Makefile 2>&1 | tee trace.log

# 步骤2：查找变量赋值
grep -E "^[+] ac_[a-z_]+=" trace.log | head -20

# 步骤3：检查变量值是否异常
# 查找包含乱码的行
grep -E "[^[:print:]]" trace.log

# 步骤4：追踪变量来源
# 在脚本中添加调试输出
echo "DEBUG: var=$var" >&2
```

**常见原因**：
- 命令替换（反引号）执行异常
- 管道命令输出错误
- 工具兼容性问题

#### 6.10.4 工具兼容性验证

**场景**：怀疑某个工具与标准行为不一致。

**验证方法**：

```bash
# 步骤1：确定工具来源
which sed
ls -la $(which sed)

# 步骤2：查看版本
sed --version  # GNU sed 会显示版本，toybox 通常不显示

# 步骤3：对比行为
# 先用 toybox 版本测试
echo "test" | sed 's/test/pass/'

# 再用 GNU 版本测试（如果已安装）
echo "test" | gsed 's/test/pass/'

# 步骤4：测试具体功能
# 例如，测试 expr 复合正则表达式
expr X"path/file" : 'X\(.*[^/]\)//*[^/][^/]*/*$' \| . : '\(.\)'
```

**已知的 toybox 问题**：

| 工具 | 问题 | 影响 | 解决方案 |
|------|------|------|----------|
| expr | 复合正则表达式 `\|` 输出乱码 | autotools 项目 | 安装 GNU coreutils |
| sed | 复杂脚本可能异常 | autotools 项目 | 安装 GNU sed |
| awk | 功能有限 | 某些脚本 | 安装 GNU awk |

#### 6.10.5 编译错误排查流程

```
1. 仔细阅读错误信息
   ↓
2. 确定错误类型：
   - 语法错误 → 检查编译器版本、标准兼容性
   - 链接错误 → 检查库依赖、库路径
   - 缺少头文件 → 检查头文件路径、sysroot
   - 权限错误 → 检查文件权限、目录权限
   ↓
3. 查找相关信息：
   - 搜索错误信息
   - 查看项目文档
   - 检查 SKILL.md 中的已知问题
   ↓
4. 尝试解决方案
   ↓
5. 验证是否解决
```

#### 6.10.6 调试技巧汇总

| 技巧 | 命令 | 用途 |
|------|------|------|
| 进程追踪 | `strace -f -o trace.log command` | 跟踪系统调用 |
| 脚本调试 | `bash -x script.sh` | 显示执行的每条命令 |
| 变量打印 | `echo "var=$var" >&2` | 输出变量值到 stderr |
| 文件检查 | `file filename` | 查看文件类型 |
| 二进制查看 | `hexdump -C file \| head` | 查看文件二进制内容 |
| 进程信息 | `cat /proc/<pid>/cmdline` | 查看进程命令行 |
| 环境检查 | `env \| sort` | 查看所有环境变量 |

### 6.11 归档文档规范

#### 6.11.1 README.md 必须包含的内容

每个软件的 README.md 应包含以下章节：

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

**补丁说明章节要求**：

必须详细解释每个修改的技术原因，包括：

```markdown
### 补丁说明

#### 修改文件
1. **file.c**: 修改原因

#### 关键修改详解

##### file.c - 功能说明

**问题背景**: 为什么需要这个修改

**技术原理**: 相关的技术知识

**解决方案**: 具体的修改方法

**代码示例**:
```c
// 修改后的代码
```

**影响**: 这个修改会带来什么影响
```

#### 6.11.2 补丁文件规范

**命名规范**：
- 单个补丁：`0001-port-for-ohos.patch`
- 多个补丁：`0001-xxx.patch`, `0002-xxx.patch`

**补丁文件格式**：
```diff
--- a/original-file.c
+++ b/modified-file.c
@@ -行号,数量 +行号,数量 @@
 上下文行（以空格开头）
-删除的行（以 - 开头）
+新增的行（以 + 开头）
 上下文行
```

**注意事项**：
- 路径应以 `a/` 和 `b/` 开头（便于 `patch -p1` 应用）
- 包含足够的上下文行（通常 3 行）
- 确保补丁可以干净地应用

### 6.12 编译项目依赖顺序

某些软件存在依赖关系，需要按正确顺序编译安装。

#### 6.12.1 推荐编译顺序

```
第一阶段：基础工具（解决 toybox 兼容性问题）
├── GNU coreutils 9.10  → 提供 GNU expr 等核心工具
└── GNU sed 4.9         → 替代 toybox sed

第二阶段：常用库
├── ncurses 6.4         → 终端库
├── readline 8.2        → 命令行编辑（依赖 ncurses）
└── gettext             → 国际化支持

第三阶段：其他软件
└── 按需编译
```

#### 6.12.2 依赖关系图

```
GNU coreutils ─────────────────────────────┐
GNU sed ───────────────────────────────────┤
                                           │
                                           ▼
ncurses ◄───────────────────────────── readline
   │
   ├──► 多数终端应用
   │
   └──► 其他依赖终端库的软件
```

#### 6.12.3 编译前检查依赖

```bash
# 检查是否已安装 GNU coreutils
which expr && expr --version | grep -i gnu

# 检查是否已安装 GNU sed
which sed && sed --version | grep -i gnu

# 检查是否已安装 ncurses
pkg-config --exists ncursesw && echo "ncurses 已安装"
```

### 6.13 问题排查案例：toybox expr bug 发现过程

本节记录了 toybox expr bug 的完整发现过程，作为问题排查的参考案例。

#### 6.13.1 问题现象

编译 ncurses 时，`config.status` 执行过程中 sed 进程卡住，生成的 Makefile 包含乱码。

#### 6.13.2 排查过程

```bash
# 第一步：找到卡住的进程
$ ps aux | grep sed
USER  PID  ... COMMAND
user  60545 ... sed s,@top_srcdir@,../<乱码>...,;t t

# 第二步：查看进程命令行
$ cat /proc/60545/cmdline | tr '\0' ' '
sed s,@top_srcdir@,../...乱码...,;t t

# 第三步：分析乱码来源
# 乱码在 $ac_top_srcdir 变量中

# 第四步：追踪 config.status
$ bash -x ./config.status --file=ncurses/Makefile 2>&1 | grep ac_dots
+ ac_dots='../<乱码>...'

# 第五步：分析 ac_dots 的计算
# ac_dots 来自 expr 命令的输出

# 第六步：对比测试
$ expr X"ncurses/Makefile" : 'X\(.*[^/]\)//*[^/][^/]*/*$' \| . : '\(.\)'
mOkk...  # toybox expr 输出乱码！

$ /path/to/gnu/expr X"ncurses/Makefile" : 'X\(.*[^/]\)//*[^/][^/]*/*$' \| . : '\(.\)'
ncurses  # GNU expr 正确！
```

#### 6.13.3 根因分析

| 因素 | 说明 |
|------|------|
| 触发条件 | config.status 使用复合正则表达式（`\|` 操作符） |
| 问题工具 | toybox expr |
| 问题表现 | 复合正则表达式输出乱码 |
| 影响范围 | 所有使用 autotools 的项目 |

#### 6.13.4 解决方案

1. 编译安装 GNU coreutils（包含 GNU expr）
2. 设置 PATH 优先使用 GNU 工具

#### 6.13.5 经验总结

1. **工具兼容性问题可能很隐蔽**：简单命令正常，复杂命令出错
2. **对比测试很重要**：与已知正确的工具对比行为
3. **追踪变量来源**：使用 `bash -x` 追踪脚本执行
4. **系统化排查**：从现象 → 进程 → 变量 → 命令 → 工具

### 6.14 工作流程经验总结

#### 6.14.1 编译新软件的推荐流程

```
1. 环境准备
   ├── 检查 PATH 是否包含 $HOME/usr/local/bin
   ├── 检查 TMPDIR 是否设置
   └── 确认已安装 GNU coreutils 和 GNU sed

2. 源码准备
   ├── 下载源码包
   ├── 创建 orig/work/verify 三个目录
   └── 在 work 目录中进行修改

3. 适配修改
   ├── 识别构建系统类型
   ├── 修改 config.guess/config.sub（Autotools）
   ├── 处理其他兼容性问题
   └── 验证编译成功

4. 补丁生成
   ├── 对比 orig 和 work 生成补丁
   ├── 在 verify 目录验证补丁
   └── 确认补丁正确

5. 归档文档
   ├── 编写 README.md（包含详细技术解释）
   ├── 检查归档目录命名是否正确
   └── 提交到知识库
```

#### 6.14.2 常见错误避免

| 错误 | 后果 | 正确做法 |
|------|------|----------|
| 跳过验证步骤 | 补丁无法应用 | 每次修改后都验证编译 |
| 直接写补丁文件 | 补丁格式错误 | 使用三目录法生成 |
| README 缺少技术细节 | 无法复现和参考 | 详细记录问题分析和解决方案 |
| 归档目录命名错误 | 难以查找 | 首字母/软件名/版本号 |
| 忽略工具兼容性 | 隐蔽的 bug | 优先安装 GNU 工具 |

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
