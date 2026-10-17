# jxrlib

jxrlib 是 Microsoft JPEG XR DevPK（设备移植包）的参考实现：JPEG XR
（HD Photo，ISO/IEC 29199-2）静态图像编解码器，产出 `libjpegxr`（编解码
核心）与 `libjxrglue`（容器/glue + BMP/TIF/PNM/HDR/YUV 文件 I/O）两个库，
以及 `JxrDecApp`/`JxrEncApp` 两个命令行工具。

- **来源**: https://github.com/4creators/jxrlib （官方 GitHub 仓库，
  本仓固定快照 f7521879862b9085318e814c6157490dd9dbbdb4，2017-06-15，
  与 Debian `1.2~git20170615.f752187` 同源；上游 2017 年后停更）
- **许可证**: BSD-2-Clause（归档内 LICENSE 全文）
- **分类**: library / 图像编解码

## 软件描述

JPEG XR 支持更高的压缩率、无损与近无损模式、宽色深（8/16/32bit、
浮点 HDR）、alpha 通道与分块解码。本库是该格式的参考实现（规格文档
`doc/JPEGXR_DPK_Spec_1.0.doc` 随源码分发），被 FreeImage、Netpbm、
ImageMagick、dvipng 等通过外链方式引用。

## 构建系统与适配

- **构建系统**: 上游手写裸 Makefile（无 configure/CMake）
- **工具链接线**: 补丁将硬编码的 `cc`/`ar`/`ranlib` 改为 `?=` 弱赋值，
  并在 CFLAGS/链接规则尾部追加 `EXTRA_CFLAGS`/`EXTRA_LDFLAGS`，由配方
  从 Conan 工具链传入（R33：不依赖 worker 裸 shell 环境变量）
- **新工具链兼容**: 显式声明 `strcodec.c` 内定义的 `_byteswap_ulong`
  （现代 clang 拒绝隐式声明）；`JXRGlueJxr.c` 补 `<stdlib.h>`/`<wchar.h>`
  包含（`wcslen` 同因）
- **headless 探针**: `JxrDecApp`/`JxrEncApp` 补 `--version` 入口
  （darkhttpd/divxcomp 先例），供 L2 冒烟与脚本化验证
- **安装布局**: 头文件按上游 `make install` 树安装到
  `include/libjxr/{common,image,image/x86,glue,test}`，与上游
  `libjxr.pc.in` 的 Cflags 一致；`cpp_info.defines` 传播
  `__ANSI__`/`DISABLE_PERF_MEASUREMENT`（结构体 ABI 锁定宏，与 pc 文件一致）
- **测试**: 上游无任何测试套件（快照审计见 test_package/MANIFEST.yml）；
  test_package 以真实 PK* API 编码->解码往返（23 断言）验证

## 工具

| 工具 | 用途 |
|------|------|
| `JxrDecApp` | JXR 解码为 BMP/TIF/PNM/HDR/YUV |
| `JxrEncApp` | 上述格式编码为 JXR（质量/子带/色彩格式可调） |

两者均支持 `--version`（本仓补丁新增的 headless 探针）。完整命令行
用法见 `JxrDecApp`（无参数时打印 usage）。

## 版本列表

| 版本 | 状态 | 适配日期 | 备注 |
|------|------|----------|------|
| 1.2-git20170615.f752187 | built | 2026-09-18 | 上游最终快照；无测试套件，消费者 API 往返 23/23 通过 |
