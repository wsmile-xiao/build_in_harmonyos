# WavPack

## 简介
混合无损/有损音频压缩编解码器，支持高压缩比的无损模式和有损模式。

## OHOS 适配
- 需修补 config.guess/config.sub 添加 HarmonyOS 平台识别
- 5.7.0 使用 autotools，5.8.1 使用 CMake

## 依赖
- 标准 C 库

## 功能验证
```bash
wavpack --version
wvunpack --version
```

## 参考
- 官网: https://www.wavpack.com/
