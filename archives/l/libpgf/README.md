# libpgf — OpenHarmony 编译档案

## 软件简介
libPGF 是 Progressive Graphics File（PGF）图像格式的参考实现：基于离散小波变换
（DWHT）的高压缩比、支持渐进式/ROI 解码的开源图像编解码库（LGPL-2.1+）。

## 功能概述
- PGF 图像编码/解码（无损与可调质量的有损模式）
- 渐进式按分辨率层级读取（Read(level)）
- ROI（感兴趣区域）解码
- 内存流/文件流多种 I/O 后端（CPGFMemoryStream/CPGFFileStream）

## OHOS 适配要点
- 上游 7.21.7 源码包的 autotools 脚手架陈旧（configure.ac 停在 7.15.32）且无预生成
  configure；CI 缺 aclocal 无法 autoreconf。源码不引用 config.h，conanfile.py 以极简
  Makefile 直接编译 src/ 下 6 个翻译单元（Decoder/Encoder/PGFimage/PGFstream/Subband/
  WaveletTransform），未运行上游 configure。
- OpenMP 由 `_OPENMP` 宏门控，不传 `-fopenmp` 即禁用；POSIX 分支有默认兜底，无需改源码。
- 纯库包（无可执行文件，无需 commands.json）；默认静态链接，另提供 shared 选项。

## 依赖关系
- 无第三方依赖（仅 libc/libc++）

## 参考资料
- [libPGF 官网](https://libpgf.org)
- [SourceForge 项目](https://sourceforge.net/projects/libpgf/)
