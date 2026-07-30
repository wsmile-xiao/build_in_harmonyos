# bpm-tools

> 音频文件节拍速度（BPM）分析工具集

## 简介

bpm-tools 是一套用于分析音频文件节拍速度（Beats Per Minute, BPM）的工具集，由 Mark Hills 开发，采用 GPL-2.0 许可证。主要包含三个工具：

- **bpm**: 核心分析工具，从 stdin 读取 44100Hz mono 32-bit float 格式的 raw audio 数据，输出分析后的 BPM 值
- **bpm-graph**: 生成 BPM 分析数据的可视化图表（依赖 gnuplot 和 sox）
- **bpm-tag**: 自动分析音频文件并添加 BPM 元数据标签（依赖 sox、metaflac/id3v2/vorbiscomment）

## OHOS 适配要点

- 纯 Makefile 项目，无 configure 脚本，直接 `make PREFIX=$DEFAULT_PREFIX CFLAGS="-fPIC -O2 -Wall" LDLIBS="-lm"` 编译
- 仅依赖 libm（数学库，系统内置，musl libc 提供），无需额外安装依赖
- bpm 命从 stdin 读取数据，无 `--version` 选项，用 `-h` 验证功能
- bpm-graph 和 bpm-tag 为 shell 脚本，依赖外部工具（sox、gnuplot 等），这些工具需要单独安装
- bpm 支持的主要选项：-h(帮助)、-m(最小BPM)、-x(最大BPM)、-f(输出格式)、-e(能量数据)、-g(自差异数据)、-v(verbose)

## 排除与替代

bpm-graph 和 bpm-tag 依赖的外部工具（sox、gnuplot、metaflac、id3v2、vorbiscomment）不在本包内提供，需通过 cmd-pkgs 或手动编译安装。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| libm | 系统内置 | 数学库（musl libc） |

## 功能验证

```bash
# 1. 基本验证：帮助信息
bpm -h

# 2. BPM 分析验证（使用合成音频数据）
python3 -c "
import struct, math, sys
RATE=44100; DUR=5; BPM=120; bps=BPM/60.0
for i in range(int(RATE*DUR)):
    t=i/RATE; p=(t*bps)%1.0
    if p<0.03: v=0.9*(1-p/0.03)
    elif p<0.1: v=0.3*(1-(p-0.03)/0.07)
    else: v=0.01
    sys.stdout.buffer.write(struct.pack('f', v))
" | bpm -m 60 -x 200
# 预期输出约 120.xxx

# 3. 格式化输出
python3 -c "...合成音频..." | bpm -f "%.1f" -m 60 -x 200

# 4. 能量数据输出
python3 -c "...合成音频..." | bpm -e energy.dat -m 60 -x 200
```

## 参考

- [官方网站](https://www.pogo.org.uk/~mark/bpm-tools/)
- [源码下载](https://www.pogo.org.uk/~mark/bpm-tools/releases/bpm-tools-0.3.tar.gz)
