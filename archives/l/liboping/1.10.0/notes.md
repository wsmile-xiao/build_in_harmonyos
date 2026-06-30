# liboping 1.10.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-11
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从官网下载源码: http://noping.cc/files/liboping-1.10.0.tar.gz
2. 使用 autoreconf -fvi 重新生成 configure（解决 config.status 临时目录权限问题）
3. 应用 HarmonyOS 平台补丁到 config.guess/config.sub（patch-autotools-ohos.pl）
4. configure --prefix=$DEFAULT_PREFIX
5. make -j2
6. make install DESTDIR=$TEST_PREFIX（staging 验证）
7. make check（通过）
8. 预编译包制作（ohc-run.py package）
9. make install（本地安装）
10. 用户验证（oping --help）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | GNU config.guess 不包含 HarmonyOS 检测 | 使用 patch-autotools-ohos.pl 补丁脚本 + 更新为最新 GNU config.guess/config.sub |
| 2 | config.status 无法创建临时目录文件 | autotools 生成的旧版 configure 使用不兼容的 shell 语法 | 使用 autoreconf -fvi 重新生成 configure |

## 源码修改

- config.guess: 替换为最新 GNU 版本（2024）并应用 HarmonyOS 平台补丁
- config.sub: 替换为最新 GNU 版本（2024）并应用 HarmonyOS 平台补丁
- 其他文件: autoreconf 重新生成的 autotools 文件（INSTALL, Makefile.in, configure 等）

## 依赖版本

- clang 15.0.4
- make 4.4.1
- automake 1.16.5
- autoconf 2.72
- libtool 2.4.7
- Perl 5.42.0

## 验证结果

```bash
$ $DEFAULT_PREFIX/bin/oping --help
Usage: oping [OPTIONS] -f filename | host [host [host ...]]
oping 1.10.0, http://noping.cc/
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| liboping-1.10.0-ohos-aarch64.tar.gz | 509K | 预编译包（含库、头文件、可执行文件） |
| liboping-1.10.0-ohos-aarch64-debug.tar.gz | 255K | Debug 符号包 |
| 0001-0019.patch | - | 19 个补丁（autotools 重新生成 + 平台检测） |

## 注意事项

1. liboping 需要 raw socket 权限才能执行 ICMP ping，安装后需要设置 cap_net_raw 权限:
   - `setcap cap_net_raw=ep $DEFAULT_PREFIX/bin/oping`
2. ncurses 未安装，noping（ncurses 版本）未编译
---

**编译结束**: 2026-06-11 14:31
**最终状态**: built
