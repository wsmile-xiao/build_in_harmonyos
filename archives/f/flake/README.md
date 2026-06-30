# flake — FLAC 音频编码器

flake 是一个开源的 FLAC（Free Lossless Audio Codec）音频编码器，由 Justin Ruggles 开发。
它采用 ffmpeg-style 的自定义 configure 脚本和 Makefile 构建系统，将 WAV 音频文件编码为无损压缩的 FLAC 格式。

## 主要特性

- 无损音频压缩编码（FLAC 格式）
- 支持 12 级压缩等级（-0 到 -12）
- 支持固定预测和 Levinson-Durbin 递归预测
- 支持可变块大小编码
- 提供静态链接库 libflake 供第三方集成
- 命令行工具，简单易用

## 版本列表

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 0.11 | published | 2026-06-17 | 首次鸿蒙平台编译，功能验证通过 |

## 鸿蒙平台编译要点

- 构建系统为 custom（ffmpeg-style configure），非标准 autoconf
- 必须传递 `--cc=clang --ar=llvm-ar --ranlib=llvm-ranlib` 适配鸿蒙工具链
- 需顺序构建（`make lib && make progs && make utils`），并行构建有竞态条件
- 无 `make check` 测试套件，需手动编码测试验证
- 需 ELF 签名后才能在鸿蒙平台执行

## 相关链接

- 官方网站: https://sourceforge.net/projects/flake-enc/
- 源码仓库: https://downloads.sourceforge.net/project/flake-enc/
