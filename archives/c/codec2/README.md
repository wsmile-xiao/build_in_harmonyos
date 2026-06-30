# Codec2

## 简介
Codec2 是一个开源的低比特率语音编码库，专为双向无线电通信设计。它提供多种编码模式（700C、700D、700E、1600、2400A/B、3200 等），以及 OFDM 调制解调器、FSK 调制解调器等功能。

## OHOS 适配
- CMake 构建系统在 OpenHarmony 上正常工作（有平台识别警告但不影响编译）
- 测试套件需要 octave，OpenHarmony 上不可用，UNITTEST 必须禁用
- LPCNet 依赖需单独编译，standalone 构建需禁用 LPCNET
- 上游 CMake 安装规则仅安装库和头文件，不安装命令行工具
- 必须使用外部构建目录（CMakeLists.txt 强制要求）

## 排除与替代
- 无

## 依赖
- 无编译依赖（standalone 构建）

## 功能验证
- pkg-config --modversion codec2 → 1.2.0
- libcodec2.so 正常安装到 $DEFAULT_PREFIX/lib/

## 参考
- 官网: https://www.rowetel.com/codec2.html
- 源码: https://github.com/drowe67/codec2