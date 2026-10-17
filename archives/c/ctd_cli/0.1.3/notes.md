# ctd_cli 0.1.3 适配笔记

## 编译环境
- 构建系统: cmake（C++20，静态库）
- 编译日期: 2026-09-22
- 编译器: clang/clang++（OHOS SDK 26.0.0.18，LLVM 15.0.4，aarch64-unknown-linux-ohos）
- 标准库: OHOS 裁剪版 libc++（libcxx-ohos，LLVM 15 配套）
- 状态: built

## 编译步骤

```bash
# 1. 下载官方 GitLab 归档（tag 为 v0.1.3，非 0.1.3）
#    https://gitlab.com/slavic-demons/korgorusze/compile_time_defined_cli/-/archive/v0.1.3/compile_time_defined_cli-v0.1.3.tar.gz
#    sha256: 33f908c2bb6dce23d2f5c3f4997e8a388867756b2c35b4d500c3add88bb98566

# 2. 探索性编译（验证补丁前失败、补丁后通过）
cmake -S . -B build -DCTD_CLI_TEST_BUILD=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build -j4
# 上游 GoogleTest 用例 16 个全部运行通过（command_line_interface_test 11 + cli_status_test 4 + function_test 1）

# 3. Conan 配方验证（ohos-aarch64 profile）
python3 scripts/ohc-run.py conan-verify ctd_cli 0.1.3
# G1/G2/G3/G4/L2/L4/L5 全部 PASS；test_package 消费者测试 + 鸿蒙专项测试 2/2 通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载报 "下载内容是 HTML" | GitLab 主页 URL 返回 HTML，不是 tarball；tag 带 v 前缀 | 用 `/-/archive/v0.1.3/compile_time_defined_cli-v0.1.3.tar.gz` 归档地址 |
| 2 | 编译报 `no member named 'find' in namespace 'std::ranges'` 等 20 处错误 | OHOS SDK clang-15 裁剪 libc++ 未提供 C++20 ranges 算法族（LLVM 16 才有） | 7 个可移植性补丁（patches/0001-0007）将 ranges 算法改写为等价 std:: 算法；投影式 find→find_if+lambda，双 range swap_ranges→三迭代器 |
| 3 | conan create 未应用补丁 | Conan 2 `export_conandata_patches` 只导出 conandata.yml 已声明的补丁，不自动扫描 patches/ 目录 | conandata.yml `patches."0.1.3"` 显式列出 7 个补丁文件 |
| 4 | test_package 链接失败：`undefined symbol: korgorusze::deserialize<std::string>` | 库只声明 deserialize<T>，std::string 特化需消费者提供（上游单测同样如此） | test.cpp / ohos_specific_test.cpp 中提供 `deserialize<std::string>` 特化 |
| 5 | 消费者测试 "parse quoted argument should succeed" 失败 | 测试场景错误：位置参数值 `-7` 以 `-` 开头被解析器当作未知选项 | 改用正值 7（库行为正确，测试场景修正） |

## 源码修改

- 0001-examples-cli_example.cpp.patch — examples 中 `std::ranges::for_each` → `std::for_each(begin,end,...)`
- 0002-src-Parse.cpp.patch — 13 处 ranges find/for_each → std::find/find_if/std::for_each（投影式 find 改写为 find_if+lambda）
- 0003-src-include-korgorusze-impl-ArgumentsContainer.h.patch — find_if_not/find/find_if/any_of → std:: 版本（begin/end）
- 0004-src-include-korgorusze-impl-Command.h.patch — all_of/sort/adjacent_find → std:: 版本
- 0005-src-include-korgorusze-impl-Function.h.patch — construct_at/destroy_at → std:: 版本；swap_ranges 双 range → 三迭代器
- 0006-src-include-korgorusze-impl-NamedArgument.h.patch — all_of → std::all_of
- 0007-src-include-korgorusze-impl-StaticString.h.patch — copy → std::copy

全部为纯可移植性改写（无 __OHOS__ 平台宏），libc++≥16 / libstdc++≥12 下无需应用。

## 依赖版本

- 无第三方编译依赖（0 个 requires）。测试阶段 googletest 经 CMake FetchContent 从官方 GitHub 拉取（03597a01 版本）。
- 工具链：clang 15.0.4（OHOS SDK 26.0.0.18）/ conan 2.29.1 / cmake 4.1.2 / make 4.4.1

## 验证结果

```bash
# 上游单元测试（探索性构建，补丁后）
command_line_interface_test: 11/11 PASSED
cli_status_test:             4/4  PASSED
function_test:               1/1  PASSED
# 合计 16/16 = 100%（全量发现数=实际执行数=通过数）

# Conan 验证（conan-verify G1-G4 + L2/L4/L5 全 PASS）
# test_package：test_ctd_cli（消费者）PASSED + test_ohos_specific（鸿蒙专项：UTF-8 中文参数/长短标志/缺参错误/空输入）PASSED
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 静态库配方（R32 os 判断、R33 无 shell 环境变量依赖） |
| conandata.yml | 官方 GitLab 归档 URL + SHA-256 + 7 补丁声明 |
| test_package/ | 消费者测试 + 鸿蒙专项测试 + MANIFEST.yml（上游 16 用例声明） |
| patches/ | 7 个 ranges→std 可移植性补丁 |
| reports/knowledge-candidate-ledger.md | 知识候选台账 + 七轴查重 + 路径决定 |
| knowledge/drafts/DRAFT-ctd_cli-0.1.3-ohos-libcxx-ranges-projection.kv/.md | 路径 B 草稿（C1） |
| knowledge/drafts/DRAFT-ctd_cli-0.1.3-gitlab-archive-url.kv/.md | 路径 B 草稿（C2） |

## 注意事项

- 本库是纯库（无 bin 产物），不产生 commands.json（R38 仅 CLI 工具需要）。
- 上游 tag 为 `v0.1.3`（带 v 前缀），版本号≠tag 名。
- 测试统计双口径：上游源码声明 16 个独立 TEST_CASE（source_declared_total=16），
  当前 OHOS 配置实例化并执行的独立可执行用例 16 个（configured_executable_total=16），
  全部通过（executed_passed_total=16），通过率 16/16=100%；另 2 个测试入口
  （fuzzing_tests 需 google/fuzztest@main、size_test 需 arm-none-eabi Cortex-M0 交叉工具链）
  不属于独立用户用例且当前配置未实例化，不纳入上游用例数（R51 口径），已在
  test_package/MANIFEST.yml 中列明分类理由。
---

**编译结束**: 2026-09-22 21:59
**最终状态**: built
