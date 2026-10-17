# tl 1.3.1 适配笔记

## 编译环境
- 构建系统: cmake（header-only C++ 库，无二进制产物）
- 编译日期: 2026-08-04
- 编译器: clang 15.0.4 / clang++
- CMake: 4.1.2
- 状态: built

## 编译步骤

```bash
# 1. 官方源码下载 + SHA256 校验
#    URL: https://github.com/TartanLlama/expected/archive/refs/tags/v1.3.1.tar.gz
#    SHA256(实际计算) = 9a04f4f472fbb5c30bf60402f1ca626c4a76987f867978d0b8a35d7ab3fb8fe7 ✓ 与任务给定值一致

# 2. 上游 CMake 配置（含 FetchContent 拉取 Catch2 v2.13.10）
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON   # exit 0

# 3. 上游测试构建
cmake --build build -j4                                          # exit 0
#    14 个测试源文件全部编译为单个可执行 tl-expected-tests

# 4. 上游测试执行（CTest + 直接运行）
ctest --test-dir build --output-on-failure                        # exit 0
./build/tl-expected-tests                                         # exit 0
#    "All tests passed (453 assertions in 37 test cases)"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 误判构建系统为 autotools | 基于 URL/仓库形态猜测，tl 实为 CMake header-only | conan-init 后人工重写 conanfile.py 为 header-library + copy 头文件模式 |
| 2 | conandata.yml sha256 为占位符 | 模板未填 | 填入实际校验值 9a04f4f4... |
| 3 | 静态 39 个 TEST_CASE 与运行时 37 个用例不一致 | 2 个用例被条件编译排除（Issue 49: `#if !(__GNUC__ <= 5)`；Issue 89: `#ifdef __cpp_deduction_guides`，C++14 无 CTAD） | 以实际运行日志为准：37 个用例全部通过，453 断言，0 失败 0 跳过 |
| 4 | 归档被 init-build 初始化到 SKILL 目录 | find_project_dir() 默认定位 SKILL 根 | 设置 OHC_PROJECT_DIR 指向 worktree 后重跑，归档落到 archives/t/tl/1.3.1/ |

## 源码修改

无。tl 1.3.1 为 header-only 库，无需补丁即可在 HarmonyOS PC (OHOS) 平台编译通过。patches/ 目录未创建。

## 依赖版本

- Catch2 v2.13.10：仅上游 tests 构建依赖（FetchContent 自动获取），非 tl 运行时/业务依赖，未写入 requirements()
- tl 本体零运行时依赖（纯头文件）

## 验证结果

```bash
# 上游测试
ctest --test-dir build --output-on-failure   # 1/1 passed, exit 0
./build/tl-expected-tests                     # 453 assertions in 37 test cases, exit 0

# Conan 包验证
conan create ...                              # 见 conan-verify 记录
```

## 注意事项

- Catch2 是上游测试构建依赖，不得误报为 tl 的运行时/业务依赖
- 上游 CMake 安装目标为 `expected`，导出包名 `tl-expected`，导入目标 `tl::expected`（package_info 中 cmake_file_name=tl-expected, cmake_target_name=tl::expected）
- 本轮状态为 built（conan-verify 通过未 upload），未写 published
---

**编译结束**: 2026-08-04 15:31
**最终状态**: built
