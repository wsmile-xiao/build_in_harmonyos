# libxdiff 0.23 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-25
- 编译器: clang 15.0.4 / clang++
- 平台: aarch64-unknown-linux-ohos (HarmonyOS)
- 状态: built

## 编译步骤

1. `./configure --prefix=$DEFAULT_PREFIX` (使用替换后的 config.guess/config.sub)
2. `make -j1` (编译库和测试工具)
3. `make install DESTDIR=$TEST_PREFIX` (staging 安装)
4. `make check` (Makefile 未定义 check 目标，手动运行 test/xregression 执行 2884 个回归测试全部通过，详见 reports/test-report.md)
5. `ohc-run.py package` (预编译包制作)
6. `make install` (安装到 $DEFAULT_PREFIX)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 源码自带 config.guess 版本 2005-08-03 太旧 | 替换为系统 automake-1.17 的 config.guess/config.sub (2023版) |
| 2 | config.status 创建临时文件 Permission denied | autoconf 2.61 使用 umask 077 创建临时目录，HMDFS 上 0700 权限目录无法写入文件 | 修改 configure 脚本中 umask 077 → umask 022 |
| 3 | make 触发 config.status --recheck 导致 configure 被重新生成 | configure 时间戳比 configure.in 旧，触发 autoconf 重新生成 | touch configure 使时间戳新于 configure.in |
| 4 | G0 干净构建验证失败 | patch 命令不支持 --input 选项 (平台限制) | 已手动验证编译通过，G0 失败为平台限制 |

## 源码修改

| 文件 | 修改内容 | 补丁 |
|------|----------|------|
| config.guess | 替换为 automake-1.17 系统版本 (识别 HarmonyOS) | 0001-config.guess.patch |
| config.h.in | autoheader 重新生成 | 0002-config.h.in.patch |
| config.sub | 替换为 automake-1.17 系统版本 | 0003-config.sub.patch |
| configure | umask 077 → umask 022 (2处) | 0004-configure.patch |

## 依赖版本

无外部依赖。仅需要系统编译器 (clang 15.0.4) 和构建工具 (make 4.4.1, automake 1.17)。

## 验证结果

```bash
# 静态链接测试
clang -I$DEFAULT_PREFIX/include -o test test.c $DEFAULT_PREFIX/lib/libxdiff.a
$ ./test
libxdiff linked successfully
sizeof(mmfile_t) = 64
sizeof(xpparam_t) = 8

# 动态链接测试
clang -I$DEFAULT_PREFIX/include -L$DEFAULT_PREFIX/lib -o test_dyn test.c -lxdiff
$ ./test_dyn
libxdiff linked successfully

# ELF 验证
$ file libxdiff.so.0.0.0
ELF shared object, 64-bit LSB arm64, not stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libxdiff-0.23-ohos-aarch64.tar.gz | 334KB | 预编译包 (lib, include, share) |
| libxdiff-0.23-ohos-aarch64-debug.tar.gz | - | 调试符号包 |

## 注意事项

1. libxdiff 是纯库 (无可执行文件)，G2 功能验证显示"无二进制文件"为正常现象
2. ldconfig 在 HarmonyOS 上不可用 (libtool 警告)，不影响安装
3. xrabin.c 有编译器警告 (shift-op-parentheses, format) 但不影响功能
---

**编译结束**: 2026-06-25 13:24
**最终状态**: built
