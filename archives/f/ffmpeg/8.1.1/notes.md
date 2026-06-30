# FFmpeg 8.1.1 编译笔记

## 基本信息
- 版本：8.1.1 "Hoare"
- 发布日期：2026-05-04
- 编译日期：2026-05-14

## 编译配置

使用以下 configure 选项编译：
```bash
./configure --prefix=/storage/Users/currentUser/usr/local \
    --enable-gpl \
    --disable-doc \
    --disable-shared \
    --enable-static \
    --disable-vulkan
```

## 编译产物

- `ffmpeg` - 主程序（约 20MB，stripped）
- `ffprobe` - 媒体分析工具（约 20MB，stripped）
- `ffmpeg_g` - 调试版本（未 stripped）
- `ffprobe_g` - 调试版本（未 stripped）

## 依赖说明

FFmpeg 编译为静态库，不依赖外部动态库。运行时依赖：
- musl libc（通过 /lib/ld-musl-aarch64.so.1）

## 鸿蒙适配注意事项

1. 二进制文件需要 ELF 签名才能在鸿蒙系统上运行
2. 使用静态编译避免动态库依赖问题
3. 禁用了 Vulkan 支持（鸿蒙系统暂不支持）

## 测试状态

- 编译成功 ✅
- 安装成功 ✅
- 运行验证：待进行（需要 ELF 签名）

## 编译结束

**编译结束**: 2026-05-20
**最终状态**: built
**制品文件**: ffmpeg-8.1.1-ohos-aarch64.tar.gz
