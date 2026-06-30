# zimg 3.0.6 编译笔记

## 编译环境
- 构建系统：autotools
- 编译器：clang 15
- 平台：aarch64-unknown-linux-ohos
- 日期：2026-05-26

## 遇到的问题

### HMDFS 文件系统权限问题

**问题描述**：
configure 脚本在 HMDFS 文件系统上运行时，config.status 无法创建临时文件：
```
./config.status[1048]: can't create ./confIMKjMm/subs1.awk: Permission denied
```

**原因分析**：
config.status 使用 `mktemp -d "./confXXXXXX"` 在当前目录创建临时目录，
但 HMDFS 文件系统不支持这种操作。

**解决方案**：
使用 VPATH 构建 + 修改 config.status：
1. 在本地文件系统（~/tmp/）创建构建目录
2. 修改 config.status，使用固定临时目录代替动态创建
3. 命令：`sed 's|tmp=.*mktemp.*|tmp="./conf_work"|' config.status > config.status.fixed`

## 编译步骤

1. 下载源码：https://github.com/sekrit-twc/zimg/archive/refs/tags/release-3.0.6.tar.gz
2. 创建 .orig 和 .work 目录
3. 运行 autogen.sh 生成 configure
4. VPATH 构建：`mkdir -p ~/tmp/build-zimg-3.0.6`
5. 运行 configure：`$BUILD_SRC_DIR/configure --prefix=$DEFAULT_PREFIX`
6. 修改 config.status 并运行
7. 编译：`make -j2`
8. 安装：`make install DESTDIR=$TEST_PREFIX`
9. 测试：`make check`（无测试用例）

## 编译产物

- libzimg.a（静态库）
- libzimg.so.2.0.0（动态库）
- zimg.h（C 头文件）
- zimg++.hpp（C++ 头文件）
- zimg.pc（pkgconfig 文件）

## 依赖

无外部依赖。

## 知识提取

这是一个典型的 HMDFS 文件系统限制导致的构建失败案例。
建议在 knowledge/graph 中记录为新的错误模式。
---

**编译结束**: 2026-05-26 16:59
**最终状态**: built
