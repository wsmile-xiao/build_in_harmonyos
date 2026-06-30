# libldac

## 简介
索尼 LDAC 蓝牙音频编解码器库，源自 AOSP 项目。LDAC 是索尼开发的高品质蓝牙音频传输技术。

## OHOS 适配
- **构建系统**: CMake（原 Android.bp，已手动转换）
- **编译器**: clang 15.0.4
- **关键问题**: 原项目使用 Android 构建系统，需手动创建 CMakeLists.txt
- **源码特点**: 所有源文件通过 #include 包含在 ldaclib.c 中

## 依赖
无额外依赖

## 功能验证
```bash
# 验证库文件
ls ~/usr/local/lib/libldacBT_enc.so
ls ~/usr/local/lib/libldacBT_abr.so
```

## 参考
- AOSP 源码: https://android.googlesource.com/platform/external/libldac
- 国内镜像: https://mirrors.ustc.edu.cn/aosp/platform/external/libldac
