# FLAC

## 简介
FLAC (Free Lossless Audio Codec) 是一种无损音频压缩编解码器，提供 `flac` 编码/解码命令行工具和 `libFLAC`/`libFLAC++` 库。

## OHOS 适配
- 需要更新 `config.guess`/`config.sub` 添加 OHOS 平台识别
- config.status 的 mktemp 在 OHOS 上可能因权限问题失败，需通过 `hints/post-configure.sh` 修复
- Shared libraries 初始构建的 RPATH 不正确，需修复
- libogg 不可用，使用 `WITH_OGG=OFF` 编译

## 依赖
- 编译工具: clang, cmake/autotools
- libogg（可选，当前不可用）

## 功能验证
```bash
flac --version         # flac 1.4.3
metaflac --version     # metaflac 1.4.3
```

## 参考
- 官网: https://xiph.org/flac/
- 源码: https://downloads.xiph.org/releases/flac/
