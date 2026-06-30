# sndio 1.10.0 适配笔记

## 编译环境
- 构建系统: custom (自定义 configure + Makefile)
- 编译日期: 2026-06-05
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. `cd ~/tmp/builds/sndio-1.10.0.work`
2. `make distclean` (清理之前的编译产物)
3. `CC=clang CXX=clang++ ./configure --prefix=$HOME/usr/local`
   - 自动检测 HarmonyOS 平台，设置 alsa=no, ldadd=-lm
   - 配置结果: dynamic=yes, static=no, alsa=no, oss=no, sun=no, rmidi=no, umidi=no
4. `make -j1` (编译成功，仅 1 个 warning)
5. `make install DESTDIR=$HOME/tmp/test-install-sndio-1.10.0` (安装成功)
6. `python3 $SKILL_ROOT/scripts/ohc-run.py verify-build sndio 1.10.0 --install-prefix ~/tmp/test-install-sndio-1.10.0/storage/Users/currentUser/usr/local` (PASS-WARN)
7. `python3 $SKILL_ROOT/scripts/ohc-run.py package sndio 1.10.0` (打包成功)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | sock.c warning: pointer sign mismatch | `abuf_wgetblk` 参数类型为 `int*`，传入 `unsigned int*` | 仅 warning，不影响编译；未修改源码 |
| 2 | verify-build G4 失败: manifest 缺少 build_system | manifest.yaml 只有嵌套的 `build.system`，缺少顶级 `build_system` | 在 manifest.yaml 添加顶级 `build_system: custom` 字段 |
| 3 | verify-build 找不到二进制文件 | DESTDIR+prefix 导致安装路径嵌套 | 传递 `--install-prefix` 参数指向实际安装路径 |

## 源码修改

无需修改源码。sndio 的 configure 脚本已内置 HarmonyOS 支持（alsa=no, ldadd=-lm），
所有 bsd-compat 函数（getpeereid, issetugid, strlcat, strlcpy, strtonum）自动编译。

## 依赖版本

- 编译器: clang (HarmonyOS NEXT 内置)
- libc: musl (ld-musl-aarch64.so.1)
- ALSA: 无（HarmonyOS NEXT 不提供 ALSA，已通过 configure 禁用）
- libm: 系统数学库 (-lm)

## 验证结果

```bash
# 二进制验证
file ~/tmp/test-install-sndio-1.10.0/storage/Users/currentUser/usr/local/bin/sndiod
# ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

# 质量门禁
python3 $SKILL_ROOT/scripts/ohc-run.py verify-build sndio 1.10.0 --install-prefix ...
# PASS-WARN (G1 ✅8, G2 ⚠️4, G3 ⚠️8, G4 ✅0)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| sndio-1.10.0-ohos-aarch64.tar.gz | 1,322,719 bytes (1291KB) | 主包: bin/{sndiod,sndioctl,aucat,midicat}, lib/libsndio.so*, include/sndio.h, pkgconfig/sndio.pc |
| sndio-1.10.0-ohos-aarch64-debug.tar.gz | 280,127 bytes (273KB) | debug符号包: .debug files for all binaries |

## 注意事项

- sndio 在 HarmonyOS NEXT 上无 ALSA 支持，编译为纯 aucat 模式（通过 sndiod daemon 通信）
- sndiod daemon 需要专用用户 `_sndio` 才能运行
- 所有 bsd-compat 函数已内嵌到 libsndio.so 中，无需额外依赖
- 编译产物均为 aarch64 ELF, musl libc 动态链接
---

**编译结束**: 2026-06-05 10:20
**最终状态**: built
