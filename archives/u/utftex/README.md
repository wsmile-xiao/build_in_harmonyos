# utftex

## 软件简介

utftex 是一个命令行工具和库，用于在等宽字体环境中美化打印数学公式，使用类似 TeX 的语法。它输出 UTF-8 编码的文本，支持大量的 Unicode 数学符号。

## 核心组件

1. **libtexprintf** - 核心库，提供 C/C++ API 来格式化数学输出，调用方式类似 printf 系列函数
2. **utftex** - 命令行工具，使用 libtexprintf 实现，支持直接在终端显示格式化的数学公式

## 主要功能

- 支持分数、数组、括号、数学符号等 TeX 语法
- 输出 UTF-8 格式，适合终端显示
- 支持多种数学字体样式（如数学斜体、手写体等）
- 适合在等宽文本应用中显示数学公式

## 示例用法

```bash
# 显示分数
utftex '\frac{\alpha}{\beta+x}'
# 输出：
#  α
# ───
# β+x

# 使用数学字体
utftex -F mathnormal '\frac{1}{a+x}'
# 输出：
#  1
# ───
# 𝑎+𝑥
```

## 依赖

无外部依赖。

## 构建系统

- autotools (configure + make)
- 需要运行 autogen.sh 生成 configure 脚本

## 鸿蒙适配说明

1. **lld 链接器问题**：OHOS SDK 的 lld 依赖 libxml2，需要使用 `-fuse-ld=bfd` 强制使用 GNU ld
2. **configure conftest 执行**：使用 `--host=aarch64-linux-ohos` 绕过 conftest 执行问题（对于简单软件可接受）
3. **umask 权限问题**：HMDFS 文件系统的 umask 077 导致权限问题，需要修改 configure 脚本中的 umask 为 022
4. **bash 路径**：测试脚本中的 `/bin/bash` 需要修改为 `/data/service/hnp/bin/bash`

## 版本历史

- 1.31 - 当前版本

## 参考链接

- 项目地址：https://github.com/bartp5/libtexprintf