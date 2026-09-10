# zxing-cpp

zxing-cpp 是用于条码识别和生成的 C++ 库，提供 QR Code、Data Matrix、Aztec、PDF417 以及多种一维码格式支持。

## OHOS 适配

- 使用 CMake 构建，默认打包静态 `libZXing.a`，避免额外的动态库签名要求。
- 保留完整核心 reader/writer 功能；关闭上游 examples、C API、Python wrapper 和测试目标，避免把测试工具依赖带入包。
- 上游 CMake target 为 `ZXing::ZXing`，Conan consumer 可直接使用同名 target。

## 用法

```cmake
find_package(ZXing CONFIG REQUIRED)
target_link_libraries(your_target PRIVATE ZXing::ZXing)
```

```cpp
#include <ZXing/ReadBarcode.h>
#include <ZXing/MultiFormatWriter.h>
```

## 验证

- 设备原生核心构建和安装：通过。
- 上游 GoogleTest UnitTest：283/283 通过。
- `test_package`：通过真实 Conan consumer 编译、链接并运行 QR encode/decode 往返测试。

## 上游

- 源码：https://github.com/zxing-cpp/zxing-cpp
- 版本：2.3.0
- 许可证：Apache-2.0
