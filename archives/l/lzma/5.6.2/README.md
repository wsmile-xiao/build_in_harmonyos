# XZ Utils 5.6.2 (lzma) 鸿蒙系统编译指南

## 概述

本文档记录了 XZ Utils 5.6.2 在鸿蒙系统上的编译适配过程。XZ Utils 是一组高性能的压缩和解压缩工具，提供了 LZMA 和 XZ 格式的支持。它包含了 `xz`、`lzma`、`xzcat` 等命令行工具，以及 `liblzma` 共享库和静态库。Python 的 `lzma` 模块也依赖 `liblzma` 来提供 LZMA/XZ 压缩支持。

## 软件信息

- **软件名称**: XZ Utils (lzma)
- **版本**: 5.6.2
- **构建系统**: Autotools (configure)
- **下载地址**: https://github.com/tukaani-project/xz/releases/download/v5.6.2/xz-5.6.2.tar.xz
- **类别**: 压缩工具/库

## 鸿蒙编译环境

- **系统**: HarmonyOS (OpenHarmony)
- **内核**: HongMeng Kernel 1.11.0
- **架构**: aarch64
- **C 库**: musl libc
- **编译器**: Clang 15.0.4 (LLVM)
- **工具链**: LLVM (llvm-ar, llvm-ranlib, llvm-nm, llvm-strip)
- **目标三元组**: aarch64-unknown-linux-ohos
- **安装前缀**: `$HOME/usr/local`

## 编译步骤

### 1. 下载并解压源码

```bash
curl -L -o xz-5.6.2.tar.xz https://github.com/tukaani-project/xz/releases/download/v5.6.2/xz-5.6.2.tar.xz
tar -xf xz-5.6.2.tar.xz
cd xz-5.6.2
```

### 2. 应用补丁

```bash
patch -p1 < 0001-add-harmonyos-support.patch
```

### 3. 配置

```bash
./configure --prefix=$HOME/usr/local
```

### 4. 编译

```bash
make
```

### 5. 安装

```bash
make install
```

## 补丁说明

### 0001-add-harmonyos-support.patch

**修改文件**:
- `build-aux/config.guess`
- `build-aux/config.sub`

**修改原因**: GNU config 的 config.guess 不识别 HarmonyOS 系统，需要添加系统检测和目标三元组输出。

#### config.guess 修改内容

1. **添加 `__OHOS__` 宏检测**: 在 C 代码片段中添加 `#elif defined(__OHOS__)` 分支，设置 `LIBC=ohos`

```diff
 #if defined(__ANDROID__)
 LIBC=android
+#elif defined(__OHOS__)
+LIBC=ohos
 #else
```

2. **添加 HarmonyOS 系统识别**: 在 `case` 分支中添加 `HarmonyOS` 的检测，根据 CPU 架构输出对应的目标三元组

```diff
+    *:HarmonyOS:*:*)
+	case "$UNAME_MACHINE" in
+	    aarch64|arm64) MACHINE=aarch64 ;;
+	    armv7*|armv8*) MACHINE=arm ;;
+	    x86_64|amd64) MACHINE=x86_64 ;;
+	    i?86) MACHINE=i686 ;;
+	    *) MACHINE="$UNAME_MACHINE" ;;
+	esac
+	GUESS=${MACHINE}-unknown-linux-ohos
+	;;
```

#### config.sub 修改内容

在操作系统验证之前添加 `ohos` 到 `linux-ohos` 的映射：

```diff
+case $os in
+    ohos*) os=linux-ohos ;;
+esac
```

此补丁与 htop/wget 的 config.guess/config.sub 补丁功能类似，但实现方式不同——通过检测 `__OHOS__` 编译器预定义宏来判断系统类型，更加通用。

## 编译特性

XZ Utils 5.6.2 在鸿蒙系统上成功启用了以下特性：

| 特性 | 支持状态 |
|------|----------|
| xz 压缩格式 | ✓ 支持 |
| lzma 压缩格式 | ✓ 支持 |
| lzma_info（流信息） | ✓ 支持 |
| 多线程压缩 | ✓ 支持 |

## 遇到的问题及解决方案

XZ Utils 5.6.2 在鸿蒙系统上编译过程顺利，仅需添加 HarmonyOS 平台识别补丁，无其他特殊问题。

## 测试验证结果

XZ Utils 编译安装成功后，可通过以下方式验证功能：

```bash
# 版本检查
$ $HOME/usr/local/bin/xz --version
xz (XZ Utils) 5.6.2

# 压缩文件
$ echo "Hello, HarmonyOS!" | xz > test.txt.xz

# 解压缩
$ xz -d test.txt.xz
$ cat test.txt
Hello, HarmonyOS!

# 使用 lzma 命令
$ echo "test data" | lzma > test.lzma
$ lzma -d test.lzma

# 使用 xzcat
$ echo "test" | xz | xzcat
test
```

## Python lzma 模块支持

Python 的 `lzma` 模块依赖 `liblzma` 共享库。安装 XZ Utils 后，确保 `liblzma.so` 在库搜索路径中，Python 即可使用 lzma 模块：

```python
import lzma

# 压缩
data = b"Hello, HarmonyOS!"
compressed = lzma.compress(data)

# 解压缩
decompressed = lzma.decompress(compressed)
print(decompressed)  # b'Hello, HarmonyOS!'
```

## 安装产物

安装后将在以下位置生成文件：

**命令行工具**:

| 命令 | 路径 | 说明 |
|------|------|------|
| xz | `$HOME/usr/local/bin/xz` | XZ 格式压缩/解压缩工具 |
| lzma | `$HOME/usr/local/bin/lzma` | LZMA 格式压缩/解压缩工具 |
| xzcat | `$HOME/usr/local/bin/xzcat` | 解压 XZ 到标准输出 |
| lzcat | `$HOME/usr/local/bin/lzcat` | 解压 LZMA 到标准输出 |
| unxz | `$HOME/usr/local/bin/unxz` | XZ 解压缩工具 |
| unlzma | `$HOME/usr/local/bin/unlzma` | LZMA 解压缩工具 |

**库文件**:

| 类型 | 路径 |
|------|------|
| 共享库 | `$HOME/usr/local/lib/liblzma.so` |
| 静态库 | `$HOME/usr/local/lib/liblzma.a` |

## 依赖说明

编译 XZ Utils 5.6.2 需要以下依赖：

- **编译工具**: clang, make

无其他外部依赖，XZ Utils 是一个自包含的压缩库。

## 注意事项

1. **Python 依赖**: Python 的 `lzma` 模块需要 `liblzma.so`，确保安装后库路径正确
2. **库路径**: 如果 Python 无法找到 `liblzma`，可能需要设置 `LD_LIBRARY_PATH`：
   ```bash
   export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
   ```

## 参考资料

- XZ Utils 官方网站: https://tukaani.org/xz/
- XZ Utils GitHub: https://github.com/tukaani-project/xz
- GNU config: https://git.savannah.gnu.org/cgit/config.git/
- 鸿蒙编译知识库: build_in_harmonyos/SKILL.md

## 版本历史

- 2026-03-22: 初始版本，完成 XZ Utils 5.6.2 鸿蒙适配
