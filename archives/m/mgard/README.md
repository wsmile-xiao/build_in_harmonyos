# mgard 1.6.0 — HarmonyOS PC 适配说明

## 概况

`MGARD` 是 Brown University / CODAR 团队开发的 MultiGrid Adaptive
Reduction of Data：张量网格上误差可控的有损科学数据压缩库（多网格
系数量化 + 线性算子，文件格式经 protobuf 序列化），附 mgard-x 后端
基础设施（SERIAL/OpenMP/CUDA/HIP/SYCL，默认 SERIAL）。

- 上游：https://github.com/CODARcode/MGARD （官方 tag tarball 1.6.0）
- 形态：cmake >= 3.19 + C++17（Ninja 生成器，bare cmake + 自发现
  ohos.toolchain.cmake，zstd 先例 ML-0035）
- 产物：`libmgard`（默认 shared）+ `bin/{mgard-x, mgard-x-autotuner,
  mgard-cpu}`（SERIAL 分支默认构建安装）
- 依赖：zlib/1.3.1（find_package）、zstd/1.5.7.1（pkg-config
  libzstd，配方写 libzstd.pc shim）；protobuf/21.12（conan 包，
  文件格式硬依赖，包内自带 protoc 与重定位 protobuf.pc）；
  catch2/3.8.1 为测试依赖（test_requires）
- 关闭项：mgard-cli（需 TCLAP 1.4，制品仓无此包）、GPU 后端、
  benchmarks、docs
- 许可证：Apache-2.0

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | conan_toolchain 报 "System is unknown HarmonyOS" | bare cmake + 自发现 ohos.toolchain.cmake（zstd 先例 ML-0035） |
| 2 | E074：HMDFS jobserver fifo EPERM | Ninja 生成器（无 jobserver fifo）+ `-j$(nproc)` 并行（zstd 先例） |
| 3 | protobuf 硬依赖（pkg_search_module + find_program PROTOC 双 REQUIRED） | require conan 包 protobuf/21.12（包内自带 protoc 与重定位 protobuf.pc），-DPROTOC 显式注入，PKG_CONFIG_PATH 追加包内 lib/pkgconfig |
| 4 | pkg_search_module(libzstd) 要求 libzstd.pc | 配方写 libzstd.pc shim 指向 conan zstd 包 |
| 5 | 上游 find_package(PkgConfig/PYTHON3) 依赖设备工具 | -DPKG_CONFIG_EXECUTABLE 指 HNP pkg-config，-DPYTHON3 候选列表自动发现（真机无 HNP python3，实际 /storage/Users/currentUser/usr/local/bin/python3） |
| 6 | 上游测试 Catch2 未找到会静默跳过 | test_requires catch2/3.8.1 + CMAKE_PREFIX_PATH；build() 直接执行 tests/mgard-tests（116 TEST_CASE，上游无 add_test） |
| 7 | HMDFS umask 077 缺省 | 所有 cmake/构建/安装命令 umask 022 前缀 |
| 8 | 包内 .so 自签无效（ML-0043） | 剥 .codesign + binary-sign-tool -selfSign 重签（zstd 同款） |
| 9 | CLI 工具门禁 | 软件级 commands.json（R38） |

## 测试

### 上游

tests/ 为 Catch2 3 单元测试套件：33 个 .cpp 共 116 个 TEST_CASE
（压缩 roundtrip、文件格式、Tensor* 系列、unstructured 网格系列等）。
构建入口 tests/CMakeLists.txt（mgard-tests 可执行），上游未注册
add_test → 配方 build() 直接执行 mgard-tests 全量运行。真机通过数
以 MateBook 实测为准。

### 消费者（test_package/consumer.cpp，2 项断言）

真实编译链接 libmgard，调用公开 API
`mgard::TensorMeshHierarchy<1,float>` + `mgard::compress/decompress`
（include/mg/compress.hpp）：① max abs error <= tolerance（误差可控
保证）② 压缩字节数 < 原始字节数（压缩有效性）。test_package build()
先校验包内 libmgard + 头目录存在，防破坏性负测试 fallback（R34/L1e）。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.6.0 | prepared | 首次适配，待真机验证（Windows 阶段 2026-09-27 完成） |
