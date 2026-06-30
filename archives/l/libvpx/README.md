# libvpx

## 简介

libvpx 是 VP8/VP9 视频编解码库，Google 开发，用于 WebM 视频格式。

## OHOS 适配要点

### rtcd.h 头文件生成（关键）

libvpx 使用 rtcd.pl Perl 脚本生成运行时 CPU 检测头文件：
- vp8_rtcd.h, vp9_rtcd.h, vpx_dsp_rtcd.h, vpx_scale_rtcd.h

**解决方案**：
```bash
perl build/make/rtcd.pl --arch=arm64 --sym=vpx_scale_rtcd --config=libs-arm64-linux-gcc.mk vpx_scale/vpx_scale_rtcd.pl > vpx_scale_rtcd.h
perl build/make/rtcd.pl --arch=arm64 --sym=vpx_dsp_rtcd --config=libs-arm64-linux-gcc.mk vpx_dsp/vpx_dsp_rtcd_defs.pl > vpx_dsp_rtcd.h
perl build/make/rtcd.pl --arch=arm64 --sym=vp8_rtcd --config=libs-arm64-linux-gcc.mk vp8/common/rtcd_defs.pl > vp8_rtcd.h
perl build/make/rtcd.pl --arch=arm64 --sym=vp9_rtcd --config=libs-arm64-linux-gcc.mk vp9/common/vp9_rtcd_defs.pl > vp9_rtcd.h
```

### 编译器设置

系统只有 clang，需要设置环境变量：
```bash
CC=clang CXX=clang++ ./configure --target=arm64-linux-gcc --prefix=$DEFAULT_PREFIX
```

## 依赖

无外部依赖（纯 C 库）

## 功能验证

```bash
vpxenc --help
vpxdec --help
pkg-config --modversion vpx
```

## 参考

- https://github.com/webmproject/libvpx
- https://www.webmproject.org/code/