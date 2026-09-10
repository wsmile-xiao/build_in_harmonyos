# pipes-sh 1.3.0 适配笔记

## 基本信息
- 上游: https://github.com/pipeseroni/pipes.sh
- 版本: 1.3.0 (2018-02)
- 语言: 纯 Bash 脚本
- License: MIT
- 构建: 无编译，Makefile install 复制脚本到 bin

## 适配过程

### 构建系统
pipes.sh 是纯 Bash 脚本，`make all` 是空操作。Makefile 已有 DESTDIR 支持：
```
make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
```
但 Conan 配方使用 `copy()` 直接安装更简单，无需调用 Makefile。

### 依赖
- bash (>=4) — 运行时依赖
- ncurses (tput) — 运行时依赖

### OHOS 特殊处理
1. HMDFS 文件系统下 `chmod` 可能不生效 — 在 `build()` 中显式 `os.chmod()`
2. 无需源码补丁

### test_package
验证：
1. pipes.sh 文件存在于 bin/
2. pipes.sh 可执行
3. 脚本内容包含版本号 "1.3.0"
4. man page 存在
5. LICENSE 文件存在
---

**编译结束**: 2026-09-06 02:11
**最终状态**: built
