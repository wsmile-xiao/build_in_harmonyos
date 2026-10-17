# argy 0.6.0 适配笔记

## 编译环境
- 构建系统: cmake (header-only, INTERFACE target)
- 编译日期: 2026-09-24
- 编译器: clang/clang++ 15.0.4 (OHOS aarch64 profile: ohos-aarch64)
- 状态: built

## 编译步骤

```bash
# 上游源码（官方 tag v0.6.0，tarball SHA-256 a2d18d04...）
curl -sSL -o argy-v0.6.0.tar.gz https://codeload.github.com/mshenoda/argy/tar.gz/refs/tags/v0.6.0
cmake -S . -B build -DBUILD_EXAMPLES=ON -DCMAKE_CXX_STANDARD=17
cmake --build build -j4
ctest --test-dir build          # 1/1 argy_tests Passed
./build/tests/test_argy         # doctest: 94 test cases / 187 assertions 全部通过
```

- argy 为 header-only C++17 库（单头 include/argy.hpp，零依赖），无编译阶段；
  Conan 配方 package_type=header-library，仅复制头文件与 LICENSE。
- 上游测试 tests/test_argy.cpp 使用 doctest 2.5.0（CMake 下载 doctest.h），
  单二进制 test_argy，CTest 注册 1 项 argy_tests；实测 94 test cases / 187 assertions 全部通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create 报 `Package type is 'library', but no 'shared' option declared` | header-only 库不应声明为普通 library 类型 | package_type 改为 `header-library`（无 shared 要求） |
| 2 | conan create source() 报 `BadZipFile: File is not a zip file` | codeload URL 末段 `v0.6.0` 无 .tar.gz 扩展名，conan get() 无法识别压缩格式 | conandata.yml sources 显式加 `filename: argy-0.6.0.tar.gz`，按扩展名正确解压 |
| 3 | test_package 报 `Imported target argy::argy includes non-existent path p/include` | package() 复制头文件路径错误（include/include/argy.hpp），包内 include 为空 | package() 用 `src=source_folder/include` + `dst=package_folder/include` 精确复制 |
| 4 | G1 配方完整性检查要求 build()/export_sources()/apply_conandata_patches | 门禁按通用配方结构校验 | header-only 配方补空 build()（apply_conandata_patches）+ export_sources() |

## 依赖版本

- 零依赖（header-only）
- doctest 2.5.0（仅上游测试构建时下载，非库依赖）

## 验证结果

```bash
# 上游测试（OHOS 本机 clang 15 构建）
ctest --test-dir build --output-on-failure
# 1/1 Test #1: argy_tests Passed
./build/tests/test_argy
# [doctest] test cases:  94 |  94 passed | 0 failed | 0 skipped
# [doctest] assertions: 187 | 187 passed | 0 failed
# conan-verify: G1-G4 全部 PASS（conan create + test_package 消费者测试通过）

# 消费者验证（test_package/test.cpp 透过公开 argy.hpp 调用 CliParser API）
conan create archives/a/argy/0.6.0 -pr:h=ci/conan/profiles/ohos-aarch64 ...
# test package build 通过，消费者测试运行成功
```

## 知识候选观察

- 候选 1（header-only 配方结构）：header-only 库 conanfile 需 package_type=header-library +
  显式 filename 字段 + 精确 include 复制路径，否则 G2/G4 失败。对应知识图谱 E276/E321/E392
  已有相关覆盖，需按七轴查重确认新增差异。
- 候选 2（codeload URL 无扩展名）：`https://codeload.github.com/<org>/<repo>/tar.gz/refs/tags/<tag>`
  末段无 .tar.gz，conan get() 报 BadZipFile；conandata 加 filename 解决（E392 同口径，查重确认）。
---

**编译结束**: 2026-09-24 09:20
**最终状态**: built
