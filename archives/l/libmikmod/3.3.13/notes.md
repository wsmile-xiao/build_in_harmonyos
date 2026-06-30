# libmikmod 3.3.13 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. `ohc-run.py init-build libmikmod 3.3.13 --url=https://sourceforge.net/projects/mikmod/files/libmikmod/3.3.13/libmikmod-3.3.13.tar.gz`
2. 安装依赖: alsa-lib 1.2.12 (cmd-pkgs预编译包), SDL2 2.30.0 (cmd-pkgs预编译包)
3. 用 `patch-autotools-ohos.pl` 修补 config.guess/config.sub (E007)
4. 修补 config.status 中的 umask 077 问题 (HMDFS限制)
5. `./configure --prefix=$DEFAULT_PREFIX && make -j1 && make install DESTDIR=$TEST_PREFIX`
6. `make check` (无测试套件)
7. `ohc-run.py verify-build` → G1-G4 PASS
8. `ohc-run.py package` → libmikmod-3.3.13-ohos-aarch64.tar.gz (1700KB)
9. `make install` (不带DESTDIR) → 用户验证通过
10. `ohc-run.py finish libmikmod 3.3.13 published` → built

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess无法识别HarmonyOS | GNU config.guess不包含HarmonyOS检测分支 | 用patch-autotools-ohos.pl打补丁(E007) |
| 2 | config.status无法创建临时目录 | HMDFS上umask 077创建目录导致Permission denied | 去除config.status中umask 077,使用普通mktemp |

## 源码修改

- 0001-autotools-config.guess.patch: HarmonyOS系统识别+__OHOS__ LIBC检测
- 0002-autotools-config.sub.patch: ohos-linux triplet支持
- 0003-config.status.patch: 去除umask 077修复HMDFS权限问题

## 依赖版本

- alsa-lib 1.2.12 (预编译包)
- SDL2 2.30.0 (预编译包)

## 验证结果

```bash
$DEFAULT_PREFIX/bin/libmikmod-config --version → 3.3.13
pkg-config --modversion libmikmod → 3.3.13
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libmikmod-3.3.13-ohos-aarch64.tar.gz | 1700KB | 预编译包 |
| libmikmod-3.3.13-ohos-aarch64-debug.tar.gz | 225KB | 调试符号包 |

## 注意事项

- libmikmod是音频库(模块音乐播放),configure时检测到ALSA和OSS驱动
- config.status的umask 077问题是HMDFS文件系统限制,需要手动修复
- make check无测试套件,此为正常行为
---
**编译结束**: 2026-05-25 23:36
**最终状态**: built
---

**编译结束**: 2026-05-26 19:49
**最终状态**: built
