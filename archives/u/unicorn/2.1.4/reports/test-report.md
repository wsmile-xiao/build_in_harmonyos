# Test Report — unicorn 2.1.4

## Build Status
- **Compiler**: clang (OHOS SDK)
- **Build System**: CMake (src/) + setuptools (Python bindings)
- **Build Status**: success

## Test Results
- **test_package**: 1/1 passed (unicorn version API + C library presence)
- **L0 checks**: pass
- **L1 checks**: pass
- **L2 checks**: pass
- **L4 checks**: pass
- **L5 checks**: pass

## Known Issues
- C 模拟器默认构建所有架构耗时较长，配方限制 UNICORN_ARCH=arm64 缩短编译时间
