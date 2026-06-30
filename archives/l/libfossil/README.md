# libfossil

**版本控制系统库** - Fossil SCM 的核心 C 库

## 软件简介

libfossil 是 Fossil SCM (Simple Configuration Management) 的核心库，提供了版本控制、文档管理、Wiki 等功能的底层实现。Fossil 是一个分布式版本控制系统，由 SQLite 作者 D. Richard Hipp 设计开发。

**核心特点**:
- 单文件设计（amalgamation）：整个库编译为单个 .c 和 .h 文件
- 基于 SQLite：使用 SQLite 作为底层存储引擎
- 轻量高效：代码简洁，依赖少，适合嵌入式场景
- 完整功能：支持版本控制、时间线、Wiki、Ticket 系统等

**适用场景**:
- 嵌入式设备上的版本控制客户端
- 需要轻量级 SCM 解决方案的应用
- Fossil SCM 的扩展开发
- 对 SQLite 生态有依赖的项目

## 鸿蒙平台适配

**编译状态**: ✅ 已发布
**版本**: 0.20250730.1700
**构建系统**: Makefile（自定义）
**编译日期**: 2026-06-04

**适配要点**:
- 原始 tarball 为 amalgamation 包，无 Makefile，需自定义构建脚本
- 依赖 sqlite3 和 zlib（通过预编译包安装）
- 支持 DESTDIR 模式（符合 R20 铁律）
- 已通过功能测试（94.3% 成功率）

## 使用方式

### 安装（通过预编译包）

```bash
# 解压预编译包
tar -xzf libfossil-0.20250730.1700-ohos-aarch64.tar.gz

# 安装到本地
cp -r libfossil-0.20250730.1700-ohos-aarch64/include ~/usr/local/include/
cp -r libfossil-0.20250730.1700-ohos-aarch64/lib ~/usr/local/lib/
```

### 编译依赖程序

```c
#include "libfossil.h"

int main() {
    // 使用 libfossil API
    fsl_buffer buf = fsl_buffer_empty;
    fsl_buffer_append(&buf, "Hello", 5);
    fsl_buffer_clear(&buf);
    return 0;
}
```

编译命令:
```bash
clang -o myapp myapp.c \
  -I~/usr/local/include \
  -L~/usr/local/lib \
  -lfossil -lsqlite3 -lz \
  -Wl,-rpath,~/usr/local/lib
```

## 依赖关系

**运行时依赖**:
- sqlite3 >= 3.49.1（预编译包已安装）
- zlib >= 1.3.1（预编译包已安装）

**构建依赖**:
- clang（编译器）
- llvm-ar / llvm-ranlib（静态库工具）
- pkg-config（依赖检测）

## 版本历史

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 0.20250730.1700 | published | 2026-06-04 | 首次适配，功能完整 |

## 详细文档

- [编译笔记](0.20250730.1700/notes.md)
- [功能测试报告](0.20250730.1700/reports/functional-test-report.md)
- [补丁说明](0.20250730.1700/patches/0001-Makefile.patch)

## 许可证

BSD-2-Clause-FreeBSD

## 相关链接

- 官方网站: https://fossil-scm.org
- 项目主页: https://savannah.nongnu.org/projects/libfossil
- 源码下载: https://download.savannah.nongnu.org/releases/libfossil/