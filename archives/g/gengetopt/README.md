# gengetopt

## 软件描述

**gengetopt** 是一个 GNU 工具，用于自动生成 C/C++ 程序的命令行参数解析代码。

它从一个 `.ggo` 文件（gengetopt input file）读取参数定义，生成一个完整的 `cmdline_parser()` 函数，该函数使用 GNU getopt_long 来解析命令行参数、验证参数并提供详细的帮助信息。

### 主要功能

- 自动生成命令行解析器代码（C/C++）
- 支持短选项（`-a`）和长选项（`--option`）
- 支持可选参数、必选参数、多值参数
- 支持参数分组和依赖关系
- 自动生成帮助文本和版本信息
- 支持从配置文件读取参数
- 生成符合 GNU 标准的代码

### 使用场景

- 快速为 C/C++ 程序添加命令行参数支持
- 避免手动编写繁琐的 getopt_long 代码
- 生成可维护的命令行解析代码
- 适用于需要复杂参数处理的程序

## 已编译版本

| 版本 | 状态 | 编译日期 | 下载 |
|------|------|----------|------|
| 2.23 | built | 2026-06-09 | [gengetopt-2.23-ohos-aarch64.tar.gz](2.23/packaging/gengetopt-2.23-ohos-aarch64.tar.gz) |

## 官方资源

- **官方网站**: https://www.gnu.org/software/gengetopt/
- **源码下载**: https://ftp.gnu.org/gnu/gengetopt/
- **文档**: https://www.gnu.org/software/gengetopt/manual/

## 编译信息

- **构建系统**: GNU Autotools
- **编译器**: Clang 15.0.4
- **目标平台**: HarmonyOS aarch64
- **安装路径**: `/storage/Users/currentUser/usr/local`

## 快速使用

### 从预编译包安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- gengetopt 2.23
```

### 基本用法

创建一个 `.ggo` 文件定义参数：

```
package "myprogram"
version "1.0"

option "input" i "Input file" string required
option "output" o "Output file" string required
option "verbose" v "Verbose output" flag off
```

运行 gengetopt 生成解析器代码：

```bash
gengetopt --input myprogram.ggo
```

生成的文件：
- `cmdline.c`: 解析器实现
- `cmdline.h`: 解析器头文件

在程序中使用：

```c
#include "cmdline.h"

int main(int argc, char **argv) {
    struct gengetopt_args_info args_info;
    if (cmdline_parser(argc, argv, &args_info) != 0) {
        return 1;
    }

    // 使用 args_info.input, args_info.output, args_info.verbose_flag

    cmdline_parser_free(&args_info);
    return 0;
}
```

## 注意事项

- HarmonyOS 版本使用 VPATH 构建（在独立 build 目录编译）
- 现代 autoconf 需手动定义 PACKAGE/VERSION 宏
- help2man 非必需，不影响核心二进制编译

---

*Last updated: 2026-06-09*