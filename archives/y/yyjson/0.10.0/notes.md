# yyjson 0.10.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-24
- 编译器: clang/clang++
- 状态: built

## 源码核验
- URL: https://github.com/ibireme/yyjson/archive/refs/tags/0.10.0.tar.gz
- SHA256: 0d901cb2c45c5586e3f3a4245e58c2252d6b24bf4b402723f6179523d389b165
- 版本: 0.10.0 (git tag 0.10.0)

## 依赖检查
- W0 预检: 无第三方依赖（纯 C 库，yyjson 是自包含的 ANSI C JSON 库）
- conan 制品仓: 无依赖需要检查

## 编译步骤

```bash
# CMake 配置 (静态库，关闭测试/文档/fuzzer)
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF \
  -DYYJSON_BUILD_TESTS=OFF -DYYJSON_BUILD_FUZZER=OFF \
  -DYYJSON_BUILD_MISC=OFF -DYYJSON_BUILD_DOC=OFF

# 编译和安装
make -j1
make install DESTDIR=$HOME/tmp/test-install-yyjson-0.10.0
```

CMake 配置通过，编译成功，无错误无警告。
产物: libyyjson.a, yyjson.h, yyjson-config.cmake, yyjson.pc

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake "System is unknown" 警告 | OHOS 平台未被 CMake 原生识别 | 非阻塞警告，不影响编译结果 |
| 2 | lang-preflight 误判为 mixed | doc/doxygen/html/ 下的 .js 文件被统计为 nodejs | 删除生成的 doc/doxygen 目录后重新检测通过 (c↔cpp 兼容族) |
| 3 | GitHub 直接下载超时 | 网络访问 GitHub 受限 | 使用 Python urllib 下载获取 SHA256 |

## 源码修改

无补丁，源码无需修改即可在 OHOS 平台编译通过。

## 上游测试

### 测试清点
上游 `test/` 目录包含 12 个测试文件（test_*.c）和 4 个编译验证文件（compile_*.c/cpp）。
CMake `YYJSON_BUILD_TESTS=ON` 时注册 12 个 CTest 测试 + 4 个编译验证测试 = 16 个目标。

### 实际运行结果
```bash
# 构建测试
cmake .. -DYYJSON_BUILD_TESTS=ON
make -j1
ctest --output-on-failure
```

| # | 测试名称 | 结果 | 耗时 |
|---|---------|------|------|
| 1 | test_allocator | PASS | 0.07s |
| 2 | test_err_code | PASS | 0.05s |
| 3 | test_json_merge_patch | PASS | 0.02s |
| 4 | test_json_mut_val | PASS | 0.03s |
| 5 | test_json_patch | PASS | 0.03s |
| 6 | test_json_pointer | PASS | 0.03s |
| 7 | test_json_reader | PASS | 0.47s |
| 8 | test_json_val | PASS | 0.04s |
| 9 | test_json_writer | PASS | 6.85s |
| 10 | test_number | PASS | 0.47s |
| 11 | test_roundtrip | PASS | 0.02s |
| 12 | test_string | PASS | 0.07s |

总计: 12/12 通过 (100%), 0 失败, 0 跳过
---

**编译结束**: 2026-09-24 18:16
**最终状态**: built
