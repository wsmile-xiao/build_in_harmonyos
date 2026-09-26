# E747 — 静态 Boost.Test 的 `duplicate symbol: main`：BOOST_TEST_DYN_LINK=0 被 defined() 判真，用 BOOST_TEST_NO_MAIN 解

> Draft: E747-draft-7c6b97d9 — pairs with the same-stem `.kv`

## 错误特征

编译期零报错，**链接期**炸（上游三个测试可执行全挂）：

```
ld.lld: error: duplicate symbol: main
>>> defined at main.cpp
>>>            CMakeFiles/test_naive_tsearch_hdronly.dir/main.cpp.obj:(main)
>>> defined at unit_test_main.cpp
>>>            unit_test_main.o:(.text+0x5C8) in archive
>>>            /…/.conan2/p/boost4c158f4cbbd30/p/lib/libboost_unit_test_framework.a
clang-15: error: linker command failed with exit code 1 (use -v to see invocation)
```

## 根因分析

两条机制叠加，缺一不炸：

1. **conan CMakeDeps 的注入**：`header_only=False, shared=False` 的 boost 包
   在 `Boost-Target-release.cmake` 上挂 `INTERFACE_COMPILE_DEFINITIONS`
   `BOOST_TEST_DYN_LINK=0`——写包方意图是「0 = 静态模式」。
2. **boost 头用 `defined()` 判真**：`boost/test/unit_test.hpp` 生成 main 的守卫是
   ```c
   #if defined(BOOST_TEST_DYN_LINK) && defined(BOOST_TEST_MAIN) && !defined(BOOST_TEST_NO_MAIN)
   int main(int argc, char* argv[]) { return ::boost::unit_test::unit_test_main(&init_unit_test, argc, argv); }
   #endif
   ```
   对值为 0 的宏 `defined()` 同样为真 → 定义了 `BOOST_TEST_MODULE` 的上游
   `tests/main.cpp` 照样生成 main。

而静态归档 `libboost_unit_test_framework.a` 的 `unit_test_main.o` 成员
**同时**定义了 `main` 与 `boost::unit_test::unit_test_main()`（`llvm-nm
--defined-only -A` 实测两条 T 符号）。用户态 main 必然调用
`unit_test_main()` → 链接器拉入该成员 → 两个 `main`。

**调参无解**：归档成员是被 `unit_test_main()` 引用拉动的，与
`Boost_USE_STATIC_LIBS` / DYN_LINK 取反无关——「用户态 main」与「归档 main」
在这个归档下不可能共存。报错只给两处定义地址，不提任何宏，极易误判为
上游 CMakeLists 的问题。

## 解决方案

**主方案**：测试目标注入 `-DBOOST_TEST_NO_MAIN`，抑制上游 TU 生成 main：

```python
# conanfile.py generate()
tc = CMakeToolchain(self)
tc.extra_cxxflags = ["-DBOOST_TEST_NO_MAIN"]
```

归档 `unit_test_main.o` 提供唯一 `main`，其未定义符号 `init_unit_test()`
（`nm -u` 实测）正好由 `BOOST_TEST_MODULE` 生成的 TU 解析——这才是该静态
归档的设计契约。CXX flags 只作用于测试 TU，不影响 C 库本体。

原生（非 conan）对照构建等价写法：

```bash
cmake ... "-DCMAKE_CXX_FLAGS=-DBOOST_TEST_NO_MAIN"
```

**验证**（naive-tsearch 0.1.1，2026-09-25 设备）：

- 修前：`conan create` rc=1（上贴报错）、原生 build 同样链接失败；
- 修后：原生 `ctest` **3/3 Passed**；`conan create` rc=0（build() 内
  ctest 3/3 + test_package 消费者 10/10 PASS）。

## 备选

若上游拒绝该宏，备选是补丁改用包含式入口
（`boost/test/included/unit_test.hpp`，array-hash 先例）——动上游测试文件，
优先 NO_MAIN。

## 关联现象（原生构建面）

同一 Boost 工程在 CMake 4.x 原生 configure 还会先撞
`Could NOT find Boost: missing: unit_test_framework`（CMP0167：FindBoost
模块被移除但未设策略时仍走模块路径，与 CMakeDeps 的 BoostConfig 变量不兼容）
——见 E748；conan create 路径由 conan_toolchain.cmake 自动置
`CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON` 不受影响。
