# liblc3

## 简介
Low Complexity Communication Codec (LC3) 是蓝牙 LE Audio 协议指定的音频编解码器，由 Google 开发。

## OHOS 适配
- **构建系统**: meson
- **编译器**: clang 15.0.4
- **关键问题**: meson 在 HarmonyOS 环境中无法自动检测编译器，需要显式设置 CC 和 AR 环境变量
- **解决方案**: 使用 configure wrapper 脚本或 meson cross-file

## 依赖
无额外依赖

## 功能验证
```bash
# 验证库文件
ls ~/usr/local/lib/liblc3.so*
```

## 参考
- 官方仓库: https://github.com/google/liblc3
- LC3 规范: Bluetooth SIG LE Audio
