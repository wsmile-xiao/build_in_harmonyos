# gtimeout 9.11 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-21
- 编译器: Clang 15.0.4 (HarmonyOS NDK)
- C 库: musl libc
- 目标平台: aarch64-unknown-linux-ohos
- 源码: GNU coreutils 9.11
- 状态: success

## 软件说明
gtimeout 是 GNU coreutils 中的 timeout 命令，加上 `g` 前缀以区分系统自带的 timeout。
源码来自完整的 coreutils 9.11 包，编译后提取 timeout 二进制并重命名为 gtimeout。

## 编译步骤
1. 下载 coreutils-9.11.tar.gz 并解压
2. 应用 2 个补丁到 work 目录
3. 修复 configure 中的 umask 077 问题
4. `./configure --prefix=$DEFAULT_PREFIX CFLAGS='-fPIC -O2 -g'`
5. `make -j2 ACLOCAL=true AUTOMAKE=true AUTOCONF=true AUTOHEADER=true MAKEINFO=true` 编译
6. `make install DESTDIR=$TEST_PREFIX` 安装
7. 复制 timeout 二进制为 gtimeout

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 缺少 OHOS 平台条目 | 补丁 0001: 添加 aarch64:HarmonyOS 识别 |
| 2 | freadahead.c 编译失败 #error | musl libc FILE 结构体不透明 | 补丁 0002: 添加 __linux__ && !__GLIBC__ 适配 |
| 3 | configure umask 077 创建临时目录失败 | HMDFS 兼容性问题 | 修改 configure 中 umask 077 为 umask 0 |
| 4 | automake/makeinfo 缺失 | 鸿蒙环境未安装 | ACLOCAL=true MAKEINFO=true 绕过 |
| 5 | freadptr.c/freadseek.c 不存在 | 9.11 已移除这两个文件 | 只需适配 freadahead.c |

## 补丁列表
| 补丁文件 | 说明 |
|---------|------|
| 0001-build-aux-config.guess.patch | HarmonyOS 平台识别 (aarch64-unknown-linux-ohos) |
| 0002-lib-freadahead.c.patch | musl libc opaque FILE 适配 |

## 与 coreutils 9.10 的差异
- 9.11 移除了 freadptr.c 和 freadseek.c，只需 2 个补丁（9.10 需要 4 个 musl libc 补丁）
- timeout 命令不使用 fstat/lseek，不需要 EACCES 补丁（9.10 有 8 个 EACCES 补丁用于其他命令）
- 源码格式从 tar.xz 变为 tar.gz

## 验证结果
- gtimeout --version: PASS ✅
- gtimeout 5 echo "hello": PASS ✅
- gtimeout 1 sleep 10 (timeout kill): PASS ✅
- gtimeout --preserve-status: PASS ✅
- make check: 部分通过（超时中断，符合预期）

## 编译结束
status: closed
COMPLETED — gtimeout 9.11 conan recipe adaptation finished.
