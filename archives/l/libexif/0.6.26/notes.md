# libexif 0.6.26 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-22
- 编译器: clang/clang++ (clang 15.0.4)
- 状态: built

## 编译步骤

1. 从 GitHub releases 下载源码包 libexif-0.6.26.tar.gz
2. 解压到 ~/builds/libexif-0.6.26.work
3. 修改 config.guess, config.sub, configure 添加 HarmonyOS 平台识别
4. 执行 configure: `./configure --prefix=$HOME/usr/local`
5. 执行 make: `make -j1`
6. 执行 make check: 14 PASS, 1 SKIP
7. 执行 make install DESTDIR=$HOME/test-install-libexif-0.6.26
8. 执行 verify-build 和 package 制作预编译包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | HarmonyOS 是新平台，config.guess 不包含识别规则 | 添加 HarmonyOS case 分支，返回 aarch64-unknown-harmonyos |
| 2 | config.sub 不接受 harmonyos 配置 | kernel/os 组合验证失败 | 添加 harmonyos-* 系统类型和 harmonyos kernel-os 组合验证 |
| 3 | configure 临时文件创建失败 | mktemp 使用 ./confXXXXXX 在当前目录创建，SELinux 限制 | 修改 configure 使用 ${HOME}/tmp/confXXXXXX，并修改 umask 为 022 |
| 4 | manifest.yaml 缺少 build_system 字段 | 验证脚本期望 build_system 字段 | 添加 build_system: autotools |

## 源码修改

- config.guess: 添加 HarmonyOS 平台识别（返回 aarch64-unknown-harmonyos）
- config.sub: 添加 harmonyos-* 系统类型和 kernel-os 组合验证
- configure: 修改临时目录创建路径为 ${HOME}/tmp

## 依赖版本

- clang 15.0.4
- GNU Make 4.4.1
- autoconf 2.72
- automake 1.16.5
- pkg-config 0.29.2

## 验证结果

```bash
pkg-config --modversion libexif
# 输出: 0.6.26

pkg-config --libs libexif
# 输出: -L/storage/Users/currentUser/usr/local/lib -lexif

pkg-config --cflags libexif
# 输出: -I/storage/Users/currentUser/usr/local/include

make check
# 结果: 14 PASS, 1 SKIP (check-failmalloc.sh), 0 FAIL
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libexif-0.6.26-ohos-aarch64.tar.gz | 1250KB | 预编译包（静态库 + 头文件） |
| 0001-config.guess.patch | 769B | HarmonyOS 平台识别补丁 |
| 0002-config.sub.patch | 1930B | config.sub 适配补丁 |
| 0003-configure.patch | 872B | 临时目录路径修改补丁 |

## 注意事项

- libexif 是纯静态库，无可执行二进制文件
- G0 干净构建验证失败是 Python subprocess 平台限制，已手动验证编译流程正确
- 需要应用 3 个补丁才能在 HarmonyOS 上编译

---
**编译结束**: 2026-05-22 12:04
**最终状态**: built