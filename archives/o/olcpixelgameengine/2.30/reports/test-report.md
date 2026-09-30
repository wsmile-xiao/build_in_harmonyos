# Test Report — olcpixelgameengine 2.30

## Build Status
- **Compiler**: clang 15.0.4 (aarch64-unknown-linux-ohos, OHOS SDK 26.0.0.18)
- **Build System**: none（单头文件 C++17 库，header-only 打包）
- **Build Status**: success（conan create 通过；G1-G4 + L2/L4/L5 门禁通过）

## Test Results
- **test_package 消费者用例**: 1/1 passed（OLC_PGE_HEADLESS 无头模式：Sprite 像素读写 / 无头 Construct / Pixel 颜色比对；ctest 1/1 Passed，0.04s）
- **test_ohos 鸿蒙专项测试**: passed（OHOS 工具链直接编译运行：Sprite 渐变填充/采样/GetPixel、无头 Construct、vi2d 运算、Pixel 常量，5 项断言 failures=0）
- **上游独立测试用例**: 0（上游无正式测试套件：无 tests/ 目录、无 ctest/GTest/pytest 注册；examples/ 6 个 TEST_*.cpp 为需窗口后端的样例程序，非独立用例，完整枚举台账见 notes.md）
- **L0 checks**: pass（JC/KC/L0 通过）
- **L1 checks**: pass
- **L2 checks**: pass
- **L4 checks**: pass
- **L5 checks**: pass

## Known Issues
- 上游头文件在 OLC_PGE_HEADLESS 模式下有 9 条 missing-override 编译告警（上游原样代码，非错误，不影响编译链接运行）
- OHOS 无上游原生窗口后端，消费方需定义 OLC_PGE_HEADLESS（上游支持的无头模式）才能编译使用本包
