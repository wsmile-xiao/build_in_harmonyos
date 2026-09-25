# cpp-yyjson 0.8.0 适配笔记

## 编译环境
- 构建系统: cmake（header-only，INTERFACE target）
- 编译日期: 2026-09-22
- 编译器: clang/clang++（OHOS SDK LLVM 15，aarch64-linux-ohos）
- 状态: published
- 依赖: yyjson/0.12.0（已发布，提供 <yyjson.h>）、gtest/1.17.0.2（测试专用）
- worktree: /storage/Users/currentUser/.oh-runner/worktrees/cpp-yyjson-0.8.0
- 分支: feat/cpp-yyjson-0.8.0

## 编译步骤

```bash
# 1. init-build（官方 tag 归档 v0.8.0，sha256 核验通过）
python3 scripts/ohc-run.py init-build cpp-yyjson 0.8.0 \
  --url=https://github.com/yosh-matsuda/cpp-yyjson/archive/refs/tags/v0.8.0.tar.gz
# 2. lang-preflight: task=cpp, detected=cpp ✅
python3 scripts/ohc-run.py lang-preflight cpp-yyjson 0.8.0 \
  --src /storage/Users/currentUser/tmp/builds/cpp-yyjson-0.8.0.work
# 3. conan-init 生成配方（改写为 CMake header-only 形态）+ 补丁
python3 scripts/ohc-run.py refresh-patch --auto cpp-yyjson 0.8.0
# 4. conan-verify（8 道门禁全部 PASS，上游测试 21/21 通过）
python3 scripts/ohc-run.py conan-verify cpp-yyjson 0.8.0
```

conan create 实际命令（G2 干净构建）：
```bash
conan create archives/c/cpp-yyjson/0.8.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```
- 编译目标：build/Release/test/cpp_yyjson_test（上游 GTest 测试二进制）
- 运行结果：21 tests PASSED（3 个套件：Writer/Reader/Readme）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `field_reflection.hpp:16 fatal error: 'source_location' file not found` | OHOS SDK libc++（LLVM 15）不提供 C++20 `<source_location>`（上游要求 LLVM 17-22） | 0002 补丁：`__has_include(<source_location>)` 守卫，缺失时 `get_function_name()` 回退 `__PRETTY_FUNCTION__`（与上游 clang-cl 分支同构） |
| 2 | `no member named 'format' in namespace 'std'`（28 处） | SDK libc++ 未实现 `<format>`（version.h 中 `__cpp_lib_format` 被禁用） | 0001 补丁：在 cpp_yyjson.hpp 内提供 `yyjson::detail::format` 最小等价实现（`{}` 占位替换，支持 bool/整数/浮点/字符串/write() 类型），`!defined(__cpp_lib_format)` 守卫 |
| 3 | `no member named 'transform'/'fill'/'equal'/'uninitialized_default_construct' in namespace 'std::ranges'` | SDK libc++ 裁剪版缺失 ranges 算法 | 0001/0003 补丁：改用 `std::transform`/`std::fill`/`std::equal` + 显式迭代器（`std::ranges::begin/end` 可用），`std::ranges::views` 块被上游 `__clang_major__ >= 16` 守卫自动排除 |
| 4 | `reference to local binding 'key'/'value' declared in enclosing function` | clang 15 未实现 C++20 P1091（lambda 捕获结构化绑定，Clang 16 起） | 0001 补丁：`for (auto&& [key, value] : obj)` 内先绑定到具名引用 `ref_key`/`ref_value` 再捕获 |
| 5 | G2 首次失败 `Error in build() line 60: cmake.configure()` 找不到 yyjsonConfig.cmake | 配方 generate() 只生成 CMakeToolchain，未生成 CMakeDeps，依赖的 CMake 包配置缺失 | conanfile.py 增加 `CMakeDeps(self).generate()` |
| 6 | `std::uint64_t`（int64 max + 1）格式化成负数 | shim 整型分支 `static_cast<long long>(v)` 溢出 | 改为保留原始类型 `std::to_string(v)`（修正后 Reader.ValueExamples/Readme.Example 通过） |
| 7 | test_package `find_package(cpp-yyjson)` 找不到包 | 上游 CMake 安装的 config 名为 `cpp_yyjsonConfig.cmake`（PROJECT_NAME= cpp_yyjson） | test_package 改 `find_package(cpp_yyjson CONFIG REQUIRED)`；package_info cmake_file_name 对齐 |
| 8 | test_package 运行抛 `bool is not constructible from JSON object` | 消费者测试 `if (!val)` 对 reader::value 走 bool 转换 | 移除该判断（`as_object()` 返回 optional 已有空值处理） |

## 源码修改

- `patches/0001-include-cpp_yyjson.hpp.patch`：格式兼容 shim + ranges 算法替换 + P1091 结构化绑定捕获修复 + std::formatter 特化按 `__cpp_lib_format` 守卫
- `patches/0002-include-field_reflection.hpp.patch`：source_location 能力守卫回退
- `patches/0003-test-test.cpp.patch`：测试适配 SDK libc++（format shim、ranges 算法替换、上游笔误 `cast<X>(serialized)` → `serialized5` 使反射往返验证真正执行）

## 依赖版本

- yyjson/0.12.0（registry: ohpcd，recipe + binary 均可用）
- gtest/1.17.0.2（registry: ohpcd）

## 验证结果

```bash
# 上游测试：21/21 通过（3 套件 2ms）
# test_package 消费者测试：1/1 通过（C++20，调用 read/as_object/as_int/write 等公开 API）
# 所有失败修复后 conan-verify 全绿：G1-G4 PASS，L2/L4/L5 跳过（无 cache 路径）
```

## 注意事項

- 本库 header-only（INTERFACE CMake target），无 bin/ 产物，无需 commands.json（R38 不适用）
- 依赖 yyjson/0.12.0 已在制品仓发布（W0/R36 通过，非本库自消费）
- 本机共享设备 inode 紧张（48M 只剩数千），构建中途出现过 ENOSPC，重试后恢复
- 上游要求 LLVM 17-22，本适配通过 3 个 portability 补丁（无平台宏，全部用 `__has_include`/feature-test 守卫）在 LLVM 15 SDK 上编译并全测试通过
---

**编译结束**: 2026-09-22 14:16
**最终状态**: published
