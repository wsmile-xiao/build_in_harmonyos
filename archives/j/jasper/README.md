# JasPer

## 简介
JasPer 是一个 JPEG-2000 编解码器实现，提供图像压缩和解压缩功能，支持 Part-1 核心编解码器。

## OHOS 适配
- 标准autotools 项目，依赖 libjpeg
- 需要标准 autotools 补丁识别 HarmonyOS 系统

## 依赖
- 编译依赖：libjpeg, clang, make
- 运行依赖：libc, libjpeg

## 功能验证
```bash
jasper --version
```

## 参考
- 源码：https://github.com/jasper-software/jasper
