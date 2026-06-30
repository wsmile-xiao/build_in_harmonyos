# flake 0.11 适配笔记

## 编译环境
- 构建系统: custom（ffmpeg-style configure script，非标准 autoconf）
- 编译日期: 2026-06-17
- 编译器: clang 15.0.4 / clang++
- 平台: HarmonyOS aarch64
- 状态: published

## 编译步骤

1. init-build: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build flake 0.11 --url=https://downloads.sourceforge.net/project/flake-enc/flake/0.11/flake-0.11.tar.bz2`
2. configure: `./configure --prefix=$DEFAULT_PREFIX --cc=clang --ar=llvm-ar --ranlib=llvm-ranlib --extra-cflags="-fPIC -O2"`
3. make: `make lib && make progs && make utils`（并行构建有竞态，需顺序构建 lib→progs→utils）
4. make install DESTDIR: `make install DESTDIR=$TEST_PREFIX`（R20 DESTDIR 模式）
5. ELF 签名: `ohc-run.py sign-elf`（鸿蒙平台必须）
6. 本地安装验证: `make install`（不带 DESTDIR）
7. 打包: `ohc-run.py package flake 0.11`（R19 禁止手动打包）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make -j2 竞态条件 | flake/Makefile 的 progs 目标依赖 libflake.a，但顶层 Makefile 的 all 目标并行调用 lib 和 progs 子目标 | 改为顺序构建：先 `make lib` → 再 `make progs` → 再 `make utils` |
| 2 | configure 默认 cc=gcc | 鸿蒙平台使用 clang 作为默认编译器，不存在 gcc | 传递 `--cc=clang` |
| 3 | configure 默认 ar=ar / ranlib=ranlib | 鸿蒙平台使用 llvm-ar 和 llvm-ranlib | 传递 `--ar=llvm-ar --ranlib=llvm-ranlib` |
| 4 | HarmonyOS uname -m 返回 aarch64 | configure 脚本的 CPU 检测不支持 aarch64，设为 unknown | 不影响编译，tune=generic 即可 |
| 5 | 二进制未签名无法执行 | 鸿蒙安全机制要求 ELF 签名 | 使用 `ohc-run.py sign-elf` 签名后可执行 |

## 源码修改

无补丁。仅通过 configure 参数适配平台，符合 R1（参数最少化）原则。

## 依赖版本

- clang 15.0.4（鸿蒙平台默认）
- llvm-ar / llvm-ranlib
- GNU Make 4.4.1
- 无外部库依赖（仅需 libm，系统自带）

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/bin/flake
Flake: FLAC audio encoder
version 0.11
(c) 2006-2007 Justin Ruggles

usage: flake [options] <input.wav> [-o output.flac]
type 'flake -h' for more details.

$ file /storage/Users/currentUser/usr/local/bin/flake
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), stripped

$ flake -q test-sine.wav -o test-sine.flac
# 输入: 16,044 bytes WAV → 输出: 10,282 bytes FLAC
# 压缩率约 36%，编码功能正常 ✅
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/flake | 79,488 bytes | FLAC 音频编码器可执行文件 |
| lib/libflake.a | 170,994 bytes | 静态链接库 |
| include/flake.h | 6,359 bytes | 头文件 |

## 预编译包

| 属性 | 值 |
|------|------|
| 文件名 | flake-0.11-ohos-aarch64.tar.gz |
| 大小 | 323,652 bytes (316KB) |
| sha256 | 757b9cb718222bffcdd7cea218b8f1bbd221c318c6a352d8c88c347b1f18e773 |
| 内容 | bin/flake, lib/libflake.a, include/flake.h |

## 注意事项

- flake 使用自定义 configure 脚本（ffmpeg-style），不支持标准 autoconf 的 --build/--host/--target 参数（R15 禁止使用这些参数）
- 必须顺序构建（lib→progs→utils），并行构建会导致竞态条件
- flake 无 --version 选项，验证方式为运行无参数或 `flake -h` 查看版本信息
- flake 无 `make check` 测试套件，需通过手动编码测试验证功能
- 鸿蒙平台需要 ELF 签名才能执行二进制文件
