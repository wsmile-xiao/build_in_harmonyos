# ngspice 42 编译笔记

## 基本信息
- 软件: ngspice (电路仿真器)
- 版本: 42
- 构建系统: autotools
- 源码来源: GitHub imr/ngspice (ngspice-42 tag)

## 编译过程

### 环境设置
- 编译器: clang 15.0.4
- 目标平台: OpenHarmony arm64 (musl libc)
- TMPDIR: /data/storage/el2/base/cache

### 源码获取
- GitHub 下载遇到嵌套源码检测问题（cppduals 子目录）
- 手动解压正确的 ngspice-ngspice-42 目录

### autogen.sh
- 运行 `./autogen.sh` 生成 configure 脚本
- 需要手动复制 ltmain.sh（libtoolize 将其放到上级目录）

### configure
- 选项: `--prefix=$DEFAULT_PREFIX --disable-debug --with-readline=no --with-ngshared=no --without-x`
- 禁用 X11 支持（缺少 Xaw 库）
- 禁用 readline（鸿蒙平台无 ncurses/readline 预编译包）

### make
- 使用 `make -j4` 编译
- 编译时间: ~3分钟
- 编译成功，无错误

### 安装验证
- `ngspice --version` 显示正确版本 (42)
- `ngspice --help` 显示帮助信息
- 程序可以正常启动

## 预编译包
- 文件: ngspice-42-ohos-aarch64.tar.gz (4.9M)
- 内容: bin/ngspice, share/ngspice/scripts/, share/man/

## 知识提取
- ngspice GitHub tarball 包含嵌套源码（cppduals），init-build 脚本可能误检测
- 需要禁用 X11 支持才能在鸿蒙平台编译
- readline/ncurses 依赖可选，禁用不影响核心功能

---
**编译结束**: 2026-05-26 19:46
**最终状态**: published
---

**编译结束**: 2026-05-26 19:47
**最终状态**: published
