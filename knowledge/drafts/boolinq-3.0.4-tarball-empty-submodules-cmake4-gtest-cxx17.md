# DRAFT-boolinq-3.0.4-tarball-empty-submodules-cmake4-gtest-cxx17：tarball 空 git 子模块 + CMake 4 版本下限 + gtest 1.17 要 C++17——header-only 库上游测试树的最小补丁法（预留条目 **E741**）

> Status: DRAFT（Reserved entry id **E741**，`tools/knowledge_id.py --claim --task boolinq-3.0.4`）
> Source: boolinq 3.0.4 HarmonyOS PC 适配（平台 id 14213，2026-09-25）
> 机器可读正文：同名 `.kv`（`yaml.safe_load` 回读 + `prescan_pattern` `re.compile` 自检通过）

## 背景

boolinq（https://github.com/k06a/boolinq ）3.0.4 是单头文件 LINQ 风格迭代器库，
上游自带 GoogleTest 测试树（40 个 `.cpp`、214 个 `TEST` 宏）挂在根 CMakeLists 下，
测试依赖通过 **git 子模块**（`externals/googletest`、`externals/benchmark`）引入。
在设备（clang 15 / CMake 4.1.2 / conan gtest 1.17.0）上按 release tarball 构建，
会**按顺序暴露三个独立边界**，任一未处理都到不了测试运行。

## 现象（错误面，按暴露顺序）

```text
1) CMake Error: Compatibility with CMake < 3.5 has been removed from CMake.
   （根 CMakeLists: CMAKE_MINIMUM_REQUIRED (VERSION 3.0)，设备 CMake 4.1.2）
2) CMake Error: The source directory ".../externals/googletest" does not contain a CMakeLists.txt file.
   （ADD_SUBDIRECTORY (externals/googletest) —— tarball 里该目录是空的，
     .gitmodules 只在 git clone --recursive 时才有内容）
3) .../gtest/gtest.h:63:10: error: ... a C++17 or later language standard is required
   （测试树 SET (CMAKE_CXX_STANDARD 11)，conan gtest 1.17.0 头实测 c++11/c++14 编译 rc=1、
     c++17 rc=0）
```

## 根因

1. **tarball ≠ git 树**：GitHub archive 不展开子模块，`ADD_SUBDIRECTORY` 指空目录即 fatal。
2. **CMake 4.x 移除 <3.5 兼容**：老项目版本下限不抬就硬错误（`-DCMAKE_POLICY_VERSION_MINIMUM`
   只是绕行，不修根因）。
3. **gtest 1.17 抬了 C++ 下限**：上游测试树钉 11/14 时必须同步抬到 17；boolinq 头本身
   无 C++17 移除特性（`auto_ptr`/`random_shuffle` 等 0 命中），抬标准不动语义。
4. 附带：上游全局 `-fprofile-arcs -ftest-coverage` 是覆盖率插桩，设备无 lcov/gcov 链路，
   纯测试构建应删除该行（覆盖率目标不构建即无影响）。

## 推荐做法（tarball-cmake-test-tree-minimal-patch）

只动测试构建树，**库头与上游测试用例零改动**（boolinq 实测 2 个补丁、40 个 `.cpp` 未动一行）：

1. 根 CMakeLists：`cmake_minimum_required` 抬到 3.15；删空子模块子目录的 `ADD_SUBDIRECTORY`
   与失效的 `ADD_DEPENDENCIES … gtest/benchmark`；
2. 测试 CMakeLists：`CMAKE_CXX_STANDARD` 11 → 17；`find_package(GTest CONFIG REQUIRED)` +
   链接名改 `GTest::gtest_main`/`GTest::gtest`（`GTest_DIR` 由配方 `generate()` 指到 conan
   gtest 包 `lib/cmake/GTest`）；删全局 gcov flags；
3. 配方 `test_requires("gtest/1.17.0")`，`build()` 里 configure+build 后**真跑**两个测试二进制、
   解析 gtest 汇总行计数（任一非零即构建失败），报 `HMBS_UPSTREAM_TEST_RESULT`；
4. 补丁经 `refresh-patch --auto` 生成，conandata `patches:` 双面登记。

反例：给 tarball 现场 clone googletest（网络 + 版本漂移 + sha 面扩大）；或只加
`-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 绕 CMake 4 错误（不修根因，下个闸再炸）。

## 复现命令（设备可直接执行，落任务目录）

```bash
R="$HOME/tmp/boolinq-3.0.4/w0/repro"; mkdir -p "$R"
curl -fsSL -o "$R/3.0.4.tar.gz" https://github.com/k06a/boolinq/archive/3.0.4.tar.gz
sha256sum "$R/3.0.4.tar.gz"   # 3cbee2b5f70ad98a8dfd1332dad0554a60628b69acb2477b5f035155fb9aed45
tar -xzf "$R/3.0.4.tar.gz" -C "$R" --strip-components=1
ls "$R/externals/googletest"   # 空（tarball 不含子模块）
cmake -S "$R" -B "$R/build" 2>&1 | grep -E "Compatibility with CMake|does not contain a CMakeLists"
# gtest 1.17 的 C++17 下限探针：
GP=$(conan cache path "gtest/1.17.0:21b17f8b2bc0e9511e276e3d57a23893067cefe5")
printf '#include <gtest/gtest.h>\nTEST(P,works){EXPECT_EQ(1,1);}\n' > "$R/gp.cpp"
/data/service/hnp/bin/clang++ -std=c++17 -I"$GP/include" -c "$R/gp.cpp" -o "$R/gp.o"   # rc=0（c++11/c++14 rc=1）
```

## 适用范围

「release tarball + 上游 CMake 测试树挂 git 子模块」的仓库（googletest/benchmark 最常见）；
一切 `cmake_minimum_required < 3.5` 老项目（CMake 4.x 设备）；conan gtest ≥1.14 系
（1.17 要 C++17）而测试树钉旧标准的配方。header-only 库另有一面：conan-verify 的
G4/L2/L4/L5 走「跳过分支并列打 ✅」（device-facts §二.17），须人工补测消费者面。

## 验证（boolinq 3.0.4 实测，2026-09-25）

- 补丁前：两处 configure 硬错误实测复现（上文 1、2）；
- 补丁后：`conan create` rc=0；上游 **214 声明 / 214 执行 / 214 通过 / 0 失败**
  （`boolinq-test` 213 + `boolinq-test14` 1）；消费者 test_package **26 断言 / 0 失败**；
- 打包头 `sha256 7a3996f7…904fb` 与 tarball 源逐字节一致（补丁未触交付面）。
