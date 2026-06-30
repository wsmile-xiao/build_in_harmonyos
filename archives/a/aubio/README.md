# aubio

aubio is a library for audio labelling. Its features include segmenting a sound file before each onset, pitch tracking, and extracting spectral descriptors.

## 描述

aubio 是一个音频标注库，主要功能包括 onset 检测、pitch 跟踪和频谱描述提取。适用于音频分析、音乐信息检索等场景。

## 已编译版本
- 0.4.9 (2026-05-25)

## 构建系统

waf (bundled v2.0.14, patched for Python 3.12 compatibility)

## 依赖
- 无外部依赖（aubio 使用内置 ooura FFT 实现）

## 特性
- onset 检测
- pitch 跟踪
- 频谱描述提取
- 内置 ooura FFT 实现
- 命令行工具：aubioonset, aubiotrack, aubionotes, aubiocut

## 使用方法
```bash
# onset 检测
aubioonset -i input.wav

# pitch 跟踪
aubiopitch -i input.wav
```

## 注意事项
- aubio 内置的 waf 2.0.14 与 Python 3.12+ 不兼容，编译前需先应用补丁
- 命令行工具不支持 --version 参数，仅支持 --help
- 如需 fftw3/sndfile/jack/avcodec/samplerate 支持，需先安装对应预编译包再 configure