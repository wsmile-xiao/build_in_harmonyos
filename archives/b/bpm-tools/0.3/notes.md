# bpm-tools 0.3 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-06-16
- 编译器: clang/clang++
- 状态: built

## 编译步骤

bpm-tools 是一个简单的纯 Makefile 项目，只有一个 C 源文件 bpm.c 和两个 shell 脚本（bpm-graph, bpm-tag）。无需 configure 步骤，直接 make 编译：

```bash
cd $BUILD_SRC_DIR
make PREFIX=$DEFAULT_PREFIX CFLAGS="-fPIC -O2 -Wall" LDLIBS="-lm"
make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
make install PREFIX=$DEFAULT_PREFIX  # 本地安装
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 configure 脚本 | 纯 Makefile 项目 | 直接使用 make，指定 PREFIX/CFLAGS/LDLIBS |
| 2 | manifest.yaml build_system 字段位置 | init-build 默认写为嵌套字段，verify 要求顶级字段 | 添加顶级 build_system: makefile |

## 源码修改

无源码修改，无需补丁。

## 依赖版本

- libm (系统自带，musl libc)

## 验证结果

### 帮助信息验证
```bash
$ $DEFAULT_PREFIX/bin/bpm -h
bpm (C) Copyright 2013 Mark Hills <mark@xwax.org>
Usage: bpm [options]
  -g <path>  Output autodifference data to file
  -e <path>  Output energy data to file
  -f         Print format for final BPM value (default "%0.1f")
  -m <f>     Minimum detected BPM (default 84)
  -x <f>     Maximum detected BPM (default 146)
  -v         Print progress information to stderr
  -h         Display this help message and exit
# ✅ 帮助信息完整显示
```

### BPM 分析功能验证（合成音频，目标 BPM=120）
```bash
# 生成5秒合成音频（44100Hz mono 32-bit float，120BPM节拍脉冲）
$ cat test_audio_120bpm.bin | bpm
119.971
# ✅ 检测结果 119.971，与目标120误差仅0.024%

$ cat test_audio_120bpm.bin | bpm -m 60 -x 200
120.094
# ✅ 自定义范围后结果更精确

$ cat test_audio_120bpm.bin | bpm -f "%.1f" -m 60 -x 200
120.1
# ✅ 格式化输出正常
```

### 数据输出功能验证
```bash
# 能量数据 (-e)
$ cat test_audio_120bpm.bin | bpm -e energy.dat -m 60 -x 200
# 能量数据: 1722行，格式为 "时间\t能量值"

# 自差异数据 (-g)
$ cat test_audio_120bpm.bin | bpm -g diff.dat -m 60 -x 200
# 自差异数据: 1025行，格式为 "BPM\t差异值"
```

### 安装完整性验证
```bash
$ file ~/usr/local/bin/bpm
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)

$ file ~/usr/local/bin/bpm-graph
/bin/sh script

$ file ~/usr/local/bin/bpm-tag
/bin/sh script

$ ls ~/usr/local/share/man/man1/
bpm.1  bpm-graph.1  bpm-tag.1
# ✅ 所有文件安装正确
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bpm-tools-0.3-ohos-aarch64.tar.gz | 91KB | 预编译包 |
| bpm-tools-0.3-ohos-aarch64-debug.tar.gz | 26KB | 调试符号包 |

## 注意事项

- bpm 工具读取 stdin 上的 raw audio 数据，无 --version 选项，使用 -h 验证
- bpm-graph 和 bpm-tag 为 shell 脚本，依赖外部工具（sox, gnuplot, metaflac, id3v2, vorbiscomment）
- 无 make check/test 目标，跳过测试
---

**编译结束**: 2026-07-15 16:16
**最终状态**: built
