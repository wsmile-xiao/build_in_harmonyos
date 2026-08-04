# SoapySDR 0.8.1 适配笔记

## 概述
- 上游版本: 0.8.1
- 构建系统: CMake (C++11)
- 上游仓库: https://github.com/pothosware/SoapySDR
- 许可证: BSL-1.0

## 适配过程
SoapySDR 是纯 CMake 项目，无外部依赖（仅需系统 libdl 和 pthread）。
Python 绑定和 Doxygen 文档为可选功能，OHOS 上关闭。

### 编译配置
- `ENABLE_PYTHON=OFF` — 无需 Python 绑定
- `ENABLE_PYTHON3=OFF` — 无需 Python3 绑定
- `ENABLE_DOCS=OFF` — 无需 Doxygen 文档
- `ENABLE_TESTS=ON` — 运行上游单元测试
- `ENABLE_APPS=ON` — 构建 SoapySDRUtil 命令行工具

### 编译产物
- `libSoapySDR.so` — 共享库
- `SoapySDRUtil` — 命令行工具
- 头文件: `include/SoapySDR/*.h`, `include/SoapySDR/*.hpp`
- CMake 配置文件: `lib/cmake/SoapySDR/`

### 上游测试
4 个单元测试（通过 CTest 运行）:
1. TestTimeConversion — 时间转换测试
2. TestFormatParser — 格式解析测试
3. TestKwargsMarkup — 键值对标记测试
4. TestConvertTypes — 类型转换测试

### 已知问题
- 无硬件设备时，SoapySDRUtil 的 `--probe` 功能不可用（正常行为）
- 无实际 SDR 设备，部分 API 无法在测试中验证（如设备枚举、流处理）