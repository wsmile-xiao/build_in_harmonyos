# json_struct 1.0.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4 / clang++（OHOS PC 工具链）
- 状态: built

## 编译步骤

```bash
# 1. 源码获取（官方 tarball，SHA-256 核验通过）
#    https://github.com/jorgen/json_struct/archive/refs/tags/1.0.2.tar.gz
#    sha256: c424ae3e8dbe6846311cb878d2d400c98a297a28eb1556961a985b6ed7b16090

# 2. 上游测试构建（header-only，无配方修复）
cmake -DCMAKE_BUILD_TYPE=Release -DJSON_STRUCT_OPT_BUILD_TESTS=ON \
  -DJSON_STRUCT_OPT_BUILD_EXAMPLES=OFF -DJSON_STRUCT_OPT_BUILD_BENCHMARKS=OFF \
  -DJSON_STRUCT_OPT_INSTALL=OFF -DJSON_STRUCT_OPT_DISABLE_PCH=ON ..
make -j4 unit-tests zero-value-test-fp-default zero-value-test-fp-fast unit-tests-cxx17

# 3. Conan 消费者验证
conan create archives/j/json_struct/1.0.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 误判构建系统为 autotools | URL 不含 cmake 关键字，_guess_build_system 默认 autotools | 手动将 manifest 的 build_system/system 修正为 cmake |
| 2 | GitHub 直连下载超时 | 执行端网络到 github.com 归档通道不稳定 | 用 codeload.github.com 官方通道预下载 tarball 并核验 SHA-256 |
| 3 | W3 JC 误报其他库 junk 文件 | 分支尚无 commit，junk_check 回退 full 整仓扫描 | commit 本库改动后走 incremental（CI pr.diff 同口径），基线文件不动 |

## 源码修改

无补丁（header-only 库，上游源码零修改；配方与测试为本仓库新增文件）

## 依赖版本

无第三方依赖（测试使用 vendored Catch2 v2.13.1）

## 验证结果

```bash
# 上游测试（cwd: $TMPDIR/builds/json_struct-1.0.2.work/build-test）
./tests/unit-tests                # All tests passed (1441 assertions in 170 test cases)
./tests/zero-value-test-fp-default # All tests passed (27 assertions in 1 test case)
./tests/zero-value-test-fp-fast    # All tests passed (27 assertions in 1 test case)
./tests/unit-tests-cxx17           # All tests passed (1476 assertions in 172 test cases)
# 全量通过率: 172/172 = 100%（台账见 reports/test-ledger.md）

# 鸿蒙专项消费者测试（test_package.cpp）
clang++ -std=c++17 -I include test_package.cpp -o test_json_struct
./test_json_struct                # json_struct OHOS consumer test: ALL PASSED
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-library 配方（INTERFACE 目标 + pkg-config） |
| conandata.yml | 官方源码 URL + SHA-256 |
| test_package/ | 鸿蒙专项消费者测试 + MANIFEST |
| reports/test-ledger.md | 上游测试完整枚举台账 |

## 注意事项

- header-only 库：`cpp_info.bindirs/libs` 置空，仅 `includedirs`，消费者
  `find_package(json_struct)` 获得 `json_struct::json_struct`
- 鸿蒙中文场景（UTF-8/emoji）与 int64/uint64 全 64 位精度在消费者测试中显式覆盖
---

**编译结束**: 2026-09-03 03:36
**最终状态**: built
