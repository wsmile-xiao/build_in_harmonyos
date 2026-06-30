# x264

## 简介

x264 是一个开源的视频编码库，用于将视频流编码为 H.264/MPEG-4 AVC 格式，广泛应用于视频处理和流媒体领域。

## OHOS 适配

- **autotools 适配**：需要修改 config.guess/config.sub 添加 HarmonyOS 平台检测
- **shebang 修正**：configure 脚本的 #!/bin/bash 需修正为 HarmonyOS bash 路径
- **PIC 编译**：使用 --enable-pic 生成位置无关代码

## 依赖

无外部依赖，为基础库。

## 功能验证

```bash
pkg-config --modversion x264
# 输出: 0.165.x
```

## 参考

- 官网: https://www.videolan.org/developers/x264.html
- 源码: https://code.videolan.org/videolan/x264