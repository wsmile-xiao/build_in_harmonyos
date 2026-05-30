# mdbtools 1.0.1 编译笔记

## 编译日期
2026-05-19

## 编译环境
- 平台: aarch64-unknown-linux-ohos
- 编译器: clang
- 构建系统: autotools

## 编译过程

### 1. 源码准备
- 下载源码: https://github.com/mdbtools/mdbtools/archive/refs/tags/v1.0.1.tar.gz
- 修改 config.guess 和 config.sub，添加 OpenHarmony 平台支持

### 2. 编译静态库
```bash
./configure --prefix=~/usr/local
make -j2
make install
```

### 3. 遇到的问题
- **libtool 安装问题**: `make install DESTDIR=...` 时 libtool 调用 install-sh 失败
  - 原因: libtool 与 HMDFS 文件系统兼容性问题
  - 解决: 手动安装静态库到 ~/usr/local/lib

### 4. 产物
- 静态库: libmdb.a, libmdbsql.a
- 头文件: mdbtools.h, mdbsql.h, mdbver.h

## 备注
可执行工具（mdb-export 等）链接失败，仅提供静态库供其他项目使用。

---
**编译结束**: 2026-05-19
**最终状态**: published (静态库可用)
