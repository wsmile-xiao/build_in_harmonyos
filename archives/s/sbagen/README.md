# sbagen

**SBaGen — Sequenced Binaural Beat Generator**（顺序双耳拍频发生器）

由 Jim Peters 编写并维护（<http://uazu.net/sbagen/>），GPL-2.0-only。本仓库
提供其在 **OpenHarmony PC（aarch64 / os=OHOS）** 上的 Conan 配方。

## 软件说明

SBaGen 从命令行读取 tone-set、序列文件（`*.sbg`）或预编程序列（`-p`），实时
合成**双耳拍频**音频：左右声道输出两路略有频差的载波，聆听者据此感知"拍频"。
可用于放松、冥想、专注等音频实验场景。

- 输出：OSS 音频设备（`/dev/dsp`）、原始数据文件/管道（`-o`/`-O`）、WAV 文件/管道（`-W`/`-WO`）
- 混音：可把生成的拍频混入既有音频（`-m`/`-M`，wav/raw 输入）
- 上游 tarball 同时附带大量文档与示例序列（focus / wave / basics / contrib 等）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| [1.4.5](1.4.5/) | built | 首次适配；零依赖、零补丁（采用上游自带 `T_POSIX` 无设备目标） |

## OpenHarmony 适配要点

1. **无音频设备**：OHOS 没有 OSS 音频设备（无 `/dev/dsp`）。上游自带
   `T_POSIX` 目标（见其 `mk-nodevdsp` 脚本）正是为此类平台准备的官方路径：
   定义 `NO_AUDIO`，输出只走文件/管道。因此**不需要任何源码补丁**。
   不带 `-o` 运行时会给出明确指引（`Use -o or -O ...`）。
2. **非标准构建**：上游没有 `configure`/`Makefile`，只有 `mk*` 脚本（shebang
   指向 `/bin/bash`，OHOS 无该路径；且默认 `-m32`）。配方直接在 `build()`
   内按 `mk-nodevdsp` 口径调用 OHOS clang 编译单文件 `sbagen.c`。
3. **零三方依赖**：只用 libc/libm/libpthread。可选的 OGG/MP3 解码器需要
   libmad 与 libvorbisidec（tremor），其中 tremor 未在 OHOS 制品仓发布，
   故**不启用**；运行时对这类输入会提示
   `Ogg/MP3 support wasn't compiled into this executable`。
4. **架构安全**：上游 tarball 内自带 32 位 x86 预编译 `sbagen` 与
   `libs/*.a`（x86 / arm32），配方只打包自建的 aarch64 产物；
   `test_package` 断言 `ELF machine == aarch64` 防回归。

## 使用

```bash
conan install --requires=sbagen/1.4.5@ohpcd/stable

# 直接输出原始/WAV 数据到文件（OHOS 无音频设备时的推荐用法）
sbagen -Q -i -o out.raw -L 00:00:10 "200+10/20"
sbagen -Q -W -i -o out.wav -L 00:00:10 "200+10/20"

# 使用上游示例序列
sbagen -S -q 1 -o seq.raw -L 00:01:00 \
    "$(conan cache path sbagen/1.4.5)/share/sbagen/examples/focus/wave-01.sbg"
```

> ⚠️ `-p <预编程序列名>` 会忽略 `-L` 写出整段序列（可达数百 MB）。
> 自动化场景请使用 `-i <tone-spec>` 配合 `-L`。
> ⚠️ 运行环境需提供可写 `TMPDIR`（OHOS `/tmp` 只读）。

## 目录

```
archives/s/sbagen/
├── README.md          # 本文件
├── commands.json      # CLI 声明（R38）
└── 1.4.5/             # 版本目录：conanfile.py / conandata.yml / test_package/ / manifest.yaml / notes.md
```
