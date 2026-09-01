# aevol 9.4.0 适配笔记

## 编译环境
- 构建系统: cmake (C++20)
- 编译日期: 2026-08-30
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos, OHOS SDK 26.0.0.18) + 适配的 libcxx/17.0.6
- 状态: built（本地完整构建 + 测试验证通过，尚未发布到制品仓）

## 背景

aevol 9.4.0 依赖现代 C++20 标准库特性（`std::format`、`std::views`、`std::from_chars(double)`），
而 OHOS SDK 自带 libc++15 全部缺失。通过适配 **libcxx/17.0.6**（详见 `archives/l/libcxx/17.0.6`）
提供这些特性后，aevol 可在 clang 15 下完整构建并通过全部测试。

## 编译步骤（等价于 conanfile.py 的 build()）

```
cmake -S <aevol-src> -B <build> \
  -DCMAKE_C_COMPILER=/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang++ \
  -DCMAKE_CXX_FLAGS="-nostdinc++ -isystem <libcxx17>/include \
      -D_LIBCPP_PROVIDES_DEFAULT_RUNE_TABLE -include ohos_libc_compat.h" \
  -DCMAKE_EXE_LINKER_FLAGS="<libcxx17>/lib/libc++.a <libcxx17>/lib/libc++abi.a" \
  -DZLIB_ROOT=<zlib-pkg> -DZLIB_INCLUDE_DIR=... -DZLIB_LIBRARY=.../libz.a \
  -DFETCHCONTENT_SOURCE_DIR_JSON=<json-3.12.0> \
  -DFETCHCONTENT_SOURCE_DIR_GOOGLETEST=<googletest-1.14.0>
cmake --build <build> -j2
ctest --output-on-failure
```

json (nlohmann 3.12.0) 与 googletest (1.14.0) 通过 `FETCHCONTENT_SOURCE_DIR_*`
从本地解压目录注入，避免构建期访问 GitHub。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS SDK clang 15 / libc++15 缺 `std::format`(127处)、`std::views`(6处)、`std::from_chars(double)` | OHOS SDK 工具链过旧（clang15 + libc++15，2022） | 适配 libcxx/17.0.6：`_LIBCPP_PROVIDES_DEFAULT_RUNE_TABLE` + `ohos_libc_compat.h` 垫片 + `construct_at` is_aggregate 分派；`from_chars(double)` 由 aevol 自带 strtod 兜底（utility.h，HAS_FROMCHARS_DOUBLE 未定义时生效） |
| 2 | clang ≥ 19 硬检查 FATAL_ERROR | aevol CMakeLists 强制 clang19+ | 补丁 0003 放宽为 ≥ 15 |
| 3 | `std::vector<FastaModifier>::emplace_back(m[1], m[2])` 编译失败 | clang15 不支持 C++20 括号聚合初始化（libc++17 construct_at 原用 `T(args...)`） | libc++17 `construct_at` 按 `std::is_aggregate` 分派（聚合→brace、非聚合→paren）；FastaModifier 调用处显式 `std::string(m[1])`（补丁 0001） |
| 4 | `RegionHandler` 成员初始化列表 `root_feature_(...)` 失败 | 同上（clang15 无括号聚合初始化） | 改 brace-init `root_feature_{...}`（补丁 0002） |
| 5 | googletest 构建需 `cxxabi.h` | test 目标缺 libcxxabi include 路径 | libcxx/17.0.6 打包 libcxxabi 头 |

## 源码修改

- `CMakeLists.txt` — clang ≥19 → ≥15（补丁 0003-cmake-relax-clang-version.patch）
- `src/libaevol/io/fasta/fasta.cpp` — `emplace_back(m[1], m[2])` → `emplace_back(std::string(m[1]), std::string(m[2]))`（补丁 0001）
- `src/libaevol/io/gff3/RegionHandler.cpp` — `root_feature_(...)` → `root_feature_{...}`（补丁 0002）
- libcxx/17.0.6 `__memory/construct_at.h` — construct_at is_aggregate 分派（libcxx 配方补丁）

## 验证结果

- 构建：**100% 成功**（aevol_create/aevol_run 各 flavor + 全部 post_treatments 可执行文件链接成功）
- 测试：**ctest 80/80 = 100% 通过**（71 个 gtest + 9 个 ctest 脚本），CTEST_EXIT=0
- 平台：aarch64-unknown-linux-ohos ELF 二进制在本机（aarch64 Linux）实测运行通过

## 依赖

- libcxx/17.0.6（本适配提供，需先发布）
- zlib/1.3.1（ohpcd 已有）
- nlohmann json 3.12.0 + googletest 1.14.0（构建期本地注入）
