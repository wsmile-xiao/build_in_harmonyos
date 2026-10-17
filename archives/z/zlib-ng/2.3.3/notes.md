# zlib-ng 2.3.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-29
- 编译器: clang
- 状态: published

## 适配说明
- ZLIB_COMPAT=OFF：使用 zlib-ng 原生 API（zng_* 函数、`<zlib-ng.h>` 头、libz-ng.a 库）
- BUILD_SHARED_LIBS=OFF：zlib-ng 虽非系统同名库（系统同名库为 zlib/libz），静态构建可避免 OHOS .so 签名复杂度
- WITH_GTEST=OFF（Conan 配方层）：Conan CI 沙箱无网络拉取 GoogleTest，上游测试通过 `test_package/run_ohos_gtest.sh` 在鸿蒙真机本地编译运行，结果见 `test_package/OHOS_TEST_REPORT.md`

## 编译步骤
```bash
cmake -B build -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
      -DBUILD_SHARED_LIBS=OFF -DZLIB_COMPAT=OFF -DWITH_GTEST=OFF
cmake --build build -j$(nproc)
cmake --install build
```

## test_package 验证
- 测试程序：`test_package/test.c`
- 验证内容：ZLIBNG_VERSION 打印 + zng_compress/zng_uncompress 压缩解压往返
- 预期输出：`PASS: zlib-ng native API is functional`

## 上游测试用例情况

zlib-ng 上游仓库使用 GoogleTest 框架（`test/test_*.cc`，需 `WITH_GTEST=ON` 启用）。
本 PR 通过 `test_package/run_ohos_gtest.sh` 在鸿蒙真机本地编译并运行上游 GoogleTest 完整套件，
详细结果见 `test_package/OHOS_TEST_REPORT.md`。

### 鸿蒙真机实测通过率（核心数据）

| 测试目标 | 用例数 | 通过 | 跳过 | 失败 | 通过率 |
|---|---|---|---|---|---|
| `gtest_zlib` (GoogleTest) | 1141 | 468 | 673 | 0 | 100%（非跳过全通过） |
| `example` (C 集成) | 1 | 1 | 0 | 0 | 100% |
| `infcover` (C 集成) | 1 | 1 | 0 | 0 | 100% |
| **合计** | **1143** | **470** | **673** | **0** | **100%** |

- 673 个 SKIPPED 均为 ARM aarch64 平台不支持的 x86/AVX/vpclmulqdq 特性变体，
  由 zlib-ng 运行时 `cpu_check_features()` 自动跳过，属预期行为，与上游 ARM CI 一致。
- 失败用例数：0。
