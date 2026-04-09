# GNU Awk (gawk) 5.3.0 - HarmonyOS 编译指南

## 概述

GNU Awk (gawk) 是一个强大的文本处理工具，是 POSIX 标准 awk 的 GNU 实现。本文档记录了 gawk 5.3.0 在 HarmonyOS 上的编译过程。

## 软件信息

| 项目 | 内容 |
|------|------|
| 名称 | GNU Awk |
| 版本 | 5.3.0 |
| 下载地址 | https://ftp.gnu.org/gnu/gawk/gawk-5.3.0.tar.xz |
| 许可证 | GPL-3.0-or-later |

## 鸿蒙环境

| 项目 | 内容 |
|------|------|
| 系统 | HarmonyOS HongMeng Kernel 1.11.0 aarch64 |
| 编译器 | clang 15.0.4 |
| 工具链 | LLVM (llvm-ar, llvm-ranlib, llvm-nm, llvm-strip) |
| 预定义宏 | `__OHOS__` |

## 编译步骤

```bash
# 1. 下载源码
cd ~/tmp
curl -L -o gawk-5.3.0.tar.xz https://ftp.gnu.org/gnu/gawk/gawk-5.3.0.tar.xz
tar -xf gawk-5.3.0.tar.xz

# 2. 应用补丁
cd gawk-5.3.0
patch -p1 < /path/to/0001-port-for-ohos.patch

# 3. 配置
./configure --prefix=$HOME/usr/local

# 4. 编译（跳过扩展模块）
make -j1

# 5. 安装主程序
mkdir -p $HOME/usr/local/bin
cp gawk $HOME/usr/local/bin/
ln -sf gawk $HOME/usr/local/bin/awk
```

## 补丁说明

### 修改文件列表

| 文件 | 修改内容 |
|------|----------|
| `build-aux/config.guess` | 添加 HarmonyOS 系统检测 |
| `build-aux/config.sub` | 添加 `linux-ohos` 和 `ohos` 支持 |
| `io.c` | 修复 fstat 对管道/终端的 EACCES 问题 |
| `main.c` | 修复 init_fds 中的 fstat 问题 |
| `posix/gawkmisc.c` | 修复 optimal_bufsize 中的 fstat 问题 |
| `custom.h` | 修复 pma.h 包含路径 |
| `extension/readdir.c` | 修复 _GNU_SOURCE 定义位置，无条件包含 dirent.h |
| `extension/filefuncs.c` | 将 _BSD_SOURCE 改为 _GNU_SOURCE |
| `extension/gawkfts.c` | 将 _BSD_SOURCE 改为 _GNU_SOURCE |
| `extension/readfile.c` | 将 _BSD_SOURCE 改为 _GNU_SOURCE |
| `extension/revtwoway.c` | 将 _BSD_SOURCE 改为 _GNU_SOURCE |

### 关键修改详解

#### 1. config.guess - HarmonyOS 检测

**问题背景**: 原始 `config.guess` 不识别 HarmonyOS 系统。

**解决方案**: 在系统检测 case 语句开头添加 HarmonyOS 检测逻辑：

```bash
*:HarmonyOS:*:*)
    case $UNAME_MACHINE in
        aarch64|arm64) MACHINE=aarch64 ;;
        armv7*|armv8*) MACHINE=arm ;;
        x86_64|amd64) MACHINE=x86_64 ;;
        i?86) MACHINE=i686 ;;
        *) MACHINE="$UNAME_MACHINE" ;;
    esac
    GUESS=${MACHINE}-unknown-linux-ohos
    ;;
```

**生成三元组**: `aarch64-unknown-linux-ohos`

#### 2. config.sub - ohos 支持

**问题背景**: `config.sub` 不识别 `ohos` 作为有效的操作系统。

**解决方案**: 
1. 在 `maybe_os` case 中添加 `linux-ohos*`
2. 在 OS 验证列表中添加 `ohos*`
3. 在 kernel-os 验证中添加 `linux-ohos*-`

#### 3. fstat EACCES 问题

**问题背景**: HarmonyOS 出于安全考虑，对管道、终端、套接字的文件描述符禁止 `fstat()` 调用，返回 EACCES 错误。

**受影响位置**:
- `io.c:iop_alloc()` - IO 缓冲区初始化
- `main.c:init_fds()` - 标准文件描述符检查
- `posix/gawkmisc.c:optimal_bufsize()` - 缓冲区大小计算

**解决方案**: 使用 `__OHOS__` 宏进行条件编译，当 `fstat()` 返回 EACCES 或 EPERM 时，使用默认值：

```c
#ifdef __OHOS__
    /* HarmonyOS returns EACCES for fstat on pipes/terminals/sockets.
     * Use default values so I/O can proceed normally. */
    if (errno == EACCES || errno == EPERM) {
        stb->st_blksize = 4096;  /* default I/O block size */
        stb->st_mode = S_IFIFO;  /* treat as pipe/FIFO */
    }
#endif
```

#### 4. custom.h - pma.h 路径

**问题背景**: 扩展模块编译时找不到 `pma.h`。

**解决方案**: 将 `#include "pma.h"` 改为 `#include "support/pma.h"`。

## 遇到的问题

### 问题 1: 扩展模块编译失败 - dirent.h 未正确包含

**现象**: 扩展模块编译时报错找不到 `DIR`、`opendir`、`struct dirent` 等。

**原因**: 
1. `_GNU_SOURCE` 定义位置不对，应该在所有系统头文件之前
2. `configure` 没有正确检测 `HAVE_DIRENT_H`
3. `_BSD_SOURCE` 在 musl libc 中不足以暴露完整的 dirent API

**解决方案**: 
- 将 `_BSD_SOURCE` 改为 `_GNU_SOURCE`
- 在 `readdir.c` 中无条件包含 `<dirent.h>`，移除 `#ifdef HAVE_DIRENT_H` 条件
- 确保 `_GNU_SOURCE` 在 `config.h` 之后、系统头文件之前定义

### 问题 2: fstat Permission denied

**现象**: `gawk: fatal: can't stat fd 0 (Permission denied)`

**原因**: HarmonyOS 对管道/终端的 fstat 返回 EACCES。

**解决方案**: 在所有 fstat 调用处添加 `__OHOS__` 条件编译处理。

## 验证测试

```bash
# 版本检查
gawk --version
# GNU Awk 5.3.0, API 4.0, PMA Avon 8-g1

# 基本功能测试
echo "hello world" | gawk '{print $1}'
# hello

# 字段操作
echo "1 2 3 4 5" | gawk '{sum=0; for(i=1;i<=NF;i++) sum+=$i; print "Sum:", sum}'
# Sum: 15

# 自定义分隔符
echo "a:b:c:d" | gawk -F: '{print $2}'
# b

# 条件判断
echo -e "apple\nbanana\ncherry" | gawk 'length($0) > 5 {print $0}'
# banana
# cherry

# 扩展模块测试
gawk -l time 'BEGIN { print strftime("%Y-%m-%d %H:%M:%S") }'
# 2026-03-19 23:42:02

gawk -l fork 'BEGIN { if (fork() == 0) print "Child"; else print "Parent" }'
# Parent
# Child
```

## 已安装的扩展模块

| 模块 | 功能 | 状态 |
|------|------|------|
| filefuncs | 文件操作函数 | ✅ |
| fnmatch | 文件名模式匹配 | ✅ |
| fork | 进程 fork | ✅ |
| inplace | 原地编辑文件 | ✅ |
| intdiv | 整数除法 | ✅ |
| ordchr | 字符/ASCII 转换 | ✅ |
| readdir | 目录读取 | ⚠️ 部分 fstat 限制 |
| readfile | 读取整个文件 | ✅ |
| revoutput | 反向输出 | ✅ |
| revtwoway | 双向管道反向 | ✅ |
| rwarray | 数组读写 | ✅ |
| time | 时间函数 | ✅ |
| testext | 测试扩展 | ✅ |

## 经验总结

1. **构建系统**: gawk 使用 Autotools，需要修改 `config.guess` 和 `config.sub`
2. **fstat 限制**: HarmonyOS 对管道/终端的 fstat 返回 EACCES，需要条件编译处理
3. **扩展模块**: 部分扩展模块可能不兼容，主程序功能完整可独立使用
4. **测试验证**: 编译后务必进行管道输入测试，确保 fstat 兼容性修复有效

## 参考资料

- GNU Awk 官方文档: https://www.gnu.org/software/gawk/manual/
- HarmonyOS 编译知识库: build_in_harmonyos/SKILL.md