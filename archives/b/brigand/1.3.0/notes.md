# brigand 1.3.0 适配笔记

## 编译环境
- 构建系统: header-only (CMake 上游测试集)
- 编译日期: 2026-09-02
- 编译器: clang/clang++ 15.0.4 (aarch64-linux-ohos)
- 状态: built

## 编译步骤

brigand 是 header-only 库，无编译产物；conanfile.py 的 build() 阶段直接编译并运行上游测试集：

```bash
# 语言预检 (R47)
ohc-run.py lang-preflight brigand 1.3.0 --src $BUILD_SRC_DIR   # detected=cpp ✅

# 上游测试编译 + 运行（49 个非 Boost 测试源，-std=c++14 -DBRIGAND_NO_BOOST_SUPPORT）
clang++ -std=c++14 -DBRIGAND_NO_BOOST_SUPPORT -I<src> -c test/<src>.cpp ...
clang++ -std=c++14 test/main.cpp <objs> -o brigand_test && ./brigand_test   # exit 0 ✅

# 配方验证（G0-G4 全通过）
ohc-run.py conan-verify brigand 1.3.0   # G2 conan create PASS ✅
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | predicate_reduction_test 在 -std=c++11 编译失败 | 上游 all_same 的 constexpr 使用 std::initializer_list，C++11 不支持 | 测试与消费者统一用 -std=c++14（上游测试本身也含 C++14 特性） |
| 2 | 消费者 include <brigand/brigand.hpp> 报缺 boost/fusion 头 | 无 Boost 时 brigand 的 adapted/fusion.hpp 仍会被包含 | package_info 注入 BRIGAND_NO_BOOST_SUPPORT define，消费者自动获得 |
| 3 | conan create 的 test_package 找不到 include 头 | package() 直接 copy 目录名 "brigand" 未生效 | 改为 copy(src=source_folder/brigand, dst=include/brigand) 逐目录复制 |
| 4 | test_package 断言引用 brigand::integral_constant | brigand 无此别名，序列元素是 std::integral_constant | 修正为 std::integral_constant；count 实为 sizeof...(T)，计数用 count_if+bind |

## 源码修改
无补丁；未改动上游源码。

## 依赖版本
- 无第三方运行时依赖（header-only）
- Boost 适配（fusion/variant 测试）未启用，符合上游无 Boost 场景

## 验证结果
- 上游测试：49/49 非 Boost 测试源编译通过，brigand_test 运行 exit 0
- 排除项：fusion_test.cpp / variant_test.cpp 需 Boost（上游仅 Boost_FOUND 时编译）
- test_package 消费者测试：编译 + 运行 exit 0（size/front/at/count_if/all/any 断言）
- conan-verify: G0-G4 PASS

## 注意事项
- 上游 tag 名为 `1.3.0`（非 v1.3.0），tarball SHA-256: 2468107c5b9ab0b56d84797dfc6636d0aae0507ae9cd6cb1acc1de85e5787acd---

**编译结束**: 2026-09-02 22:58
**最终状态**: published
---

**编译结束**: 2026-09-02 23:04
**最终状态**: published
