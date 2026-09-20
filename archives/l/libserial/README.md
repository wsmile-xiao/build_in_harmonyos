# libserial

## 简介

LibSerial 是一个跨平台的 C++ 串口编程库，提供 `SerialPort`（termios 封装）与
`SerialStream`（iostream 风格）两套 API，以及 `SerialStreamBuf` 流缓冲。纯
C++17 标准库 + POSIX termios 实现，无第三方依赖。

## OHOS 适配

### 适配要点

1. **构建开关**：上游顶层 CMakeLists 对非库目标有 REQUIRED 依赖
   （Doxygen、PythonLibs+SIP、Boost.Test），配方通过
   `LIBSERIAL_ENABLE_TESTING=OFF`、`LIBSERIAL_BUILD_EXAMPLES=OFF`、
   `LIBSERIAL_PYTHON_ENABLE=OFF`、`LIBSERIAL_BUILD_DOCS=OFF` 关闭，
   只构建并安装库本体。
2. **零补丁**：源码只用 POSIX termios/ioctl/open 等 OHOS 已支持的能力，
   交叉编译无需修改任何上游文件。
3. **产物布局**：头文件安装在 `include/libserial/`（以
   `#include <libserial/SerialPort.h>` 使用），库为 `lib/libserial.a`
   （`shared=True` 时另有 `libserial.so.1`），并安装 `libserial.pc`。

### 已知限制

- 上游自带的单元测试套件依赖物理串口（gtest 套件硬编码 `/dev/ttyUSB0`、
  `/dev/ttyUSB1`），OHOS 设备与 CI 环境均无串口硬件，无法在适配环境运行；
  无硬件依赖的库行为（默认状态、异常路径）由 `test_package` 消费者测试覆盖。
- 上游 `install(DIRECTORY libserial)` 会将 `src/libserial/Makefile.am` 一并
  安装到 `include/libserial/`，属上游安装规则原样行为，未做修改。

## 依赖

无外部依赖（C++17 标准库 + pthread）。

## 参考信息

- 上游仓库：https://github.com/crayzeewulf/LibSerial
- 许可证：BSD-3-Clause
