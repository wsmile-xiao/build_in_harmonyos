# zxing-cpp 2.3.0 版本适配记录

## 基本信息

- 上游仓库：`https://github.com/zxing-cpp/zxing-cpp`
- 上游版本：`2.3.0`
- 源码归档 SHA-256：`64e4139103fdbc57752698ee15b5f0b0f7af9a0331ecbdc492047e0772c417ba`
- 任务基线：`c84a9cdc2e54d9ba49d350dab134a5da052743a1`
- 构建系统：CMake；包类型：静态 library；默认 `shared=False`

## 问题与解决方案

| 问题 | 根因 | 解决方案 |
| --- | --- | --- |
| OHOS 默认 profile 为 gnu14，而上游目标要求 C++17 | 上游 target 使用 C++17 特性 | 在 `CMakeToolchain` 中固定 `CMAKE_CXX_STANDARD=17`、`CMAKE_CXX_STANDARD_REQUIRED=ON`，消费者也显式使用 C++17 |
| C API 入口触发 stb 获取失败 | `ZXING_C_API=ON` 会构建依赖 stb 的 wrapper；该功能不属于核心 C++ 包 | 核心包关闭 C API、examples、Python wrapper 和测试目标，保留核心 `ZXing::ZXing` |
| 上游 pkg-config 文件嵌入绝对安装前缀 | 上游模板把 CMake install prefix 写入 `libdir` 和 `includedir` | 在 `package()` 阶段改写为 `${pcfiledir}` 相对路径，保证 Conan cache 和下游安装可重定位 |

## 构建与测试

- 设备原生核心 CMake 配置、构建和安装通过，生成 `libZXing.a`、27 个公共头和 4 个 CMake 配置文件。
- 上游 UnitTest 共 283 个 case，`283 passed; 0 failed; 0 skipped; 0 not_run`；计数命令和执行命令见同目录 `test_package/MANIFEST.yml`。
- test_package 使用 `MultiFormatWriter` 生成 QR，再用 `ReadBarcode` 解码，验证尺寸、像素、文本、格式和版本；CTest `1/1` 通过，直接消费者 6/6 断言通过。
- 最终 Conan/W3 使用设备 profile `ci/conan/profiles/ohos-aarch64`，清理精确 reference 后重新 create；G0/G1/G2/G3 通过，G4/L2/L4/L5 的人工补证见 `reports/conan-verify-supplement.md`。

## 产物边界

包提供 `ZXing::ZXing`、`lib/libZXing.a`、公共头、CMake package config、可重定位 `lib/pkgconfig/zxing.pc` 和 Apache-2.0 LICENSE；不提供动态库、可执行文件、C API 或 Python wrapper。

自动 `conan-verify` 在 `--user/--channel` reference 下无法回解析 package ID，导致 G4/L2/L4/L5 显示跳过；本任务不把该 skip 当作通过，按实际 package path 和原始日志完成了人工补证。
