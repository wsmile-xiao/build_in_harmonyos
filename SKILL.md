---
# 固定元数据头（必须，AI 优先读取）
name: openharmony-compile-guide
description: 鸿蒙系统编译知识库，提供开源软件在鸿蒙系统上编译的完整指南、最佳实践和经验总结
version: 1.0.0
author: OpenSSL Community
permissions: 文件读写权限、Shell执行权限、网络访问权限（可选，用于获取参考资料）
---

# 鸿蒙系统编译知识库

## 1. Description
本技能是一个完整的鸿蒙系统编译知识库，基于 OpenSSL 在鸿蒙系统上的适配经验整理而成。当用户需要在鸿蒙系统上编译任何任何开源软件时，可以使用此技能获取：

1. 鸿蒙系统环境特点和配置
2. 编译工具链（Clang + LLVM）的使用方法
3. 预定义宏（__OHOS__）的作用和时机
4. 配置文件继承关系和最佳实践
5. 自动检测逻辑的实现方法
6. 常见编译问题的解决方案
7. 与其他平台（Linux/Android/iOS）的对比

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

## 3. How to use

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

**检测逻辑：**
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

**关键点：**
1. 检测 `uname -s` 和 `uname -r`（系统名称和内核版本）
2. 使用正则匹配 `harmonyos|openharmony`（不区分大小写）
3. 根据 `uname -m` 映射到对应的 `openharmony-*` 目标
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
例如：aarch64-unknown-ohos
```

**配置示例：**
```bash
# 使用三元组配置
./configure aarch64-unknown-ohos

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
2. 根据用户的具体问题，提供相应的解决方案
3. 如果需要，提供环境检查脚本
4. 提供与其他平台的对比，帮助用户理解差异
5. 给出最佳实践建议

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

### 6.5 调试技巧

1. ✅ 使用 -v 或 --verbose 查看详细编译过程
2. ✅ 使用 --dry-run 测试配置不实际编译
3. ✅ 使用 --debug 生成调试版本
4. ✅ 查看编译日志排查问题
5. ✅ 使用 strace 跟踪系统调用（如果可用）

## 7. 参考资料

- OpenSSL 官方文档：https://www.openssl.org/docs/
- OpenHarmony 官方网站：https://www.openharmony.cn/
- HarmonyOS 开发者文档：https://developer.huawei.com/consumer/cn/doc/
- Clang 文档：https://clang.llvm.org/docs/
- LLVM 文档：https://llvm.org/docs/
- Autotools 文档：https://www.gnu.org/software/autoconf/
- POSIX 标准：https://pubs.opengroup.org/onlinepubs/9699919699/

## 8. License

本技能遵循 MIT 许可证，可自由使用和修改。
