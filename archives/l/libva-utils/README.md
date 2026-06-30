# libva-utils

VA-API (Video Acceleration API) utilities

## 简介

libva-utils 提供 VA-API 相关的实用工具，包括：
- vainfo：显示 VA-API 信息
- 编码工具：av1encode、h264encode、hevcencode
- 解码工具：mpeg2vldemo、loadjpeg
- 视频处理工具：vavpp、vppscaling_csc

## OHOS 适配

- 需要 libva 和 libdrm 作为依赖
- meson 构建系统，需要处理 shebang 和库路径问题
- 生成 24 个实用工具二进制文件

## 依赖

- libva >= 2.0
- libdrm
- meson

## 功能验证

```bash
vainfo  # 显示 VA-API 信息
```

## 参考

- GitHub: https://github.com/intel/libva-utils