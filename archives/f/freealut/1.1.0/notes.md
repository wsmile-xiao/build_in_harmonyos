# freealut 1.1.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-17
- 编译器: clang/clang++ (15.0.4)
- 状态: published

## 编译步骤

1. `autoreconf -fi`（使用 autoconf 2.72 + automake 1.17 重新生成 configure）
2. 修改 configure 中 AS_TMPDIR 模式：`./confXXXXXX` → `${TMPDIR:-.}/confXXXXXX`，移除 `umask 077`
3. 更新 `admin/autotools/config.guess` 和 `config.sub`（来自 automake-1.17，识别 aarch64-unknown-linux-ohos）
4. 安装依赖 OpenAL（openal-soft 1.24.2，手动 cmake 编译）
5. `./configure --prefix=$DEFAULT_PREFIX`
6. `make -j2`
7. `make install DESTDIR=$TEST_PREFIX`（R20 DESTDIR 模式）
8. `make check`（通过）
9. `make install`（部署到 $DEFAULT_PREFIX）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 原始 config.guess 为 2005 年版本 | 从 automake-1.17 复制最新 config.guess/config.sub（R23） |
| 2 | config.status "Permission denied" 创建临时文件 | autoconf AS_TMPDIR 使用 `umask 077 && mktemp -d "./confXXXXXX"`，HMDFS 上 umask 077 创建的目录无法写入文件 | 修改 configure：将 `./confXXXXXX` 改为 `${TMPDIR:-.}/confXXXXXX`，移除 `umask 077` |
| 3 | 缺少 OpenAL 头文件和库 (AL/al.h, AL/alc.h) | freealut 依赖 OpenAL，cmd-pkgs 中无预编译包 | 手动编译 openal-soft 1.24.2（CMake，禁用音频后端，仅编译 WaveFile + Null 后端） |

## 源码修改

| 文件 | 修改内容 | 补丁状态 |
|------|----------|----------|
| admin/autotools/config.guess | 替换为 automake-1.17 版本（识别 aarch64-unknown-linux-ohos） | refresh-patch |
| admin/autotools/config.sub | 替换为 automake-1.17 版本 | refresh-patch |
| configure | 修改 AS_TMPDIR：`./confXXXXXX` → `${TMPDIR:-.}/confXXXXXX`，移除 `umask 077` | refresh-patch |

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| OpenAL (openal-soft) | 1.24.2 | 手动编译（cmd-pkgs 无预编译包） |

## 验证结果

```bash
# make check 通过（test_suite 程序已编译）
# Staging 产物完整：
#   lib/libalut.a (static)
#   lib/libalut.so.0.1.0 (shared) + symlinks
#   include/AL/alut.h
#   lib/pkgconfig/freealut.pc
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| freealut-1.1.0-ohos-aarch64.tar.gz | TBD | 预编译包 |

## 注意事项

- freealut 依赖 OpenAL (openal-soft)。运行时需确保 libopenal.so 在 LD_LIBRARY_PATH 中。
- openal-soft 编译时禁用了所有音频后端（ALSA/OSS/PulseAudio/JACK），仅保留 WaveFile 和 Null 后端，因为 HarmonyOS 无这些音频子系统。
- configure 脚本被 autoreconf 重新生成（autoconf 2.72），原始版本由 autoconf 2.56 生成。
- HMDFS 上 `umask 077` 导致目录权限问题是一个平台级限制，影响所有使用 autoconf AS_TMPDIR 的软件。
---

**编译结束**: 2026-06-18 11:39
**最终状态**: published
