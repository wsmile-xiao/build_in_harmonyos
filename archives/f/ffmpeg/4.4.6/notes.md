# ffmpeg 4.4.6 编译说明

## 编译环境
- OHOS SDK 26.0.0.18
- Clang 15.0.4
- 目标平台: aarch64-linux-ohos

## 编译步骤
1. 解压源码
2. configure 配置
3. make 编译
4. make install DESTDIR 安装

## 编译结果
- ffmpeg 二进制文件
- ffprobe 二进制文件
- 静态库: libavcodec.a, libavformat.a, libavutil.a, etc.

## 已知问题
- 编译警告：部分 implicit conversion warnings（不影响功能）
---

**编译结束**: 2026-05-21 15:27
**最终状态**: built
