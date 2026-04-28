# zstd-jni

## 简介
Zstandard 压缩的 JNI 封装，提供 Java 访问 Zstandard 压缩的能力。

## OHOS 适配
- JNI 项目可使用本地 jni.h 头文件编译
- 自包含，不需要外部 zstd 库
- 需修补 CMakeLists.txt 添加 JNI include 路径

## 依赖
- JDK (jni.h)
- CMake

## 参考
- 源码: https://github.com/luben/zstd-jni
