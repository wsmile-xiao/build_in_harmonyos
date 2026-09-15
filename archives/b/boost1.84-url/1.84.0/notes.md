# boost1.84-url 1.84.0 适配笔记

## 形态决策：方案 A（独立裁剪编译）

本包是 Boost 1.84.0 的**单组件包**（boost1.84-url，类似 Debian 的 libboost-url1.84 拆包形态）。

- **方案 A（采用）**：从 boost 1.84.0 官方源码包裁剪，手动 clang++ 编译 `libs/url/src` 全部 66 个源文件为 `libboost_url.a`。
- **方案 B（否决）**：`requires boost/1.84.0` 元包 + package() 暴露组件——**物理不可行**：制品仓的 boost/1.84.0 元包只编译了 filesystem/regex/program_options/iostreams 四个库，`libboost_url.a` 根本不在元包产物中，无库可暴露；且元包是 2026-05 的 header-only 定位产物。

## 编译方式

b2 在 OHOS 不兼容（SHELL 执行机制失败，E068 错误模式）。沿用 archives/b/boost/1.84.0 元包配方已验证的方法论：手动 clang++ 裁剪编译。

- 源文件集合与上游 `libs/url/build/Jamfile` 的 `glob-tree-ex ../src : *.cpp` 定义一致（66 个文件，含 detail/grammar/rfc 子目录）。
- 编译参数：`-std=c++17 -stdlib=libc++ -fPIC -O2 -DNDEBUG -DBOOST_ALL_NO_LIB -DBOOST_URL_SOURCE -DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`
- 打包：`llvm-ar rcs libboost_url.a`
- 补丁：复用元包的 0001-ohos-pthread-cancel-fix.patch（sp_thread_sleep.hpp 的 pthread_setcancelstate 在 OHOS musl 不可用，通过 BOOST_SP_NO_PTHREAD_SETCANCELSTATE 特性宏跳过，R8 合规）。

## 上游测试

Boost.URL 测试基于**自带 test_suite 框架**（`libs/url/extra/test_main.cpp` + `test_suite.hpp`），不依赖 boost.test 库——非常适合绕过 b2 直接编译运行。

**全量 92/92 通过**（按审核口径修正：上游 test/ 目录 .cpp 总数 N=92，2026-09-06 预防性扩测，参照 #8455/#8457 规则 4 条件 3 打回教训——N 必须按上游实测 .cpp 数申报）。conanfile.py build() 中全量纳入：

1. **run 类可执行 75 个**（TEST_SUITE 框架）：unit 73（70 个 Jamfile SOURCES 型 + doc_3_urls/doc_grammar/example-router 3 个额外 run 规则）+ extra/test_suite（自测空转）+ limits/limits（BOOST_URL_MAX_SIZE=16 限制编译）
2. **自包含头测试 10 个**（error_types/encoding_opts/grammar/host_type/ignore_case/optional/string_view/urls/variant/rfc-query_rule）：上游设计即无 main 无断言，仅 #include 验证头自包含——按 -fsyntax-only 编译验证纳入
3. **fuzz 5 个**（uri/absolute_uri/origin_form/relative_ref/uri_reference）：LLVMFuzzerTestOneInput 入口，用 standalone 驱动以 8 条固定语料回放验证非崩溃语义（不依赖 libFuzzer 运行时）
4. **cmake_test 1 个**：sizeof(url)>0 断言，编译运行

关键适配点：
- snippets.cpp 引用 boost::filesystem::path 符号（Jamfile 声明 `<library>/boost/filesystem`）——同步从源码树裁剪编译 libboost_filesystem.a 供测试链接（不进包产物）。filesystem 1.84 的 atomic_ref 需 C++20 而 OHOS libc++ 15 缺失，用上游 BOOST_FILESYSTEM_SINGLE_THREADED 守卫的单线程降级路径绕过
- 测试二进制 -static-libstdc++ 链接（libc++ 静态打入，绕开 libc++_shared.so rc=127 问题）
- example/router 测试需同时编译上游 example/router 的 matches.cpp + detail/impl/router.cpp（上游 run 规则的多编译单元形态）

## 依赖

无外部 conan 依赖（Boost.URL 仅依赖 boost 头文件，header-only core）。

## 验证命令

```
conan create . --user=ohpcd --channel=stable -pr:h=~/.conan2/profiles/ohos-aarch64 -pr:b=~/.conan2/profiles/ohos-aarch64 --build=missing
```
---

**编译结束**: 2026-09-06 15:10（92/92 全量扩测复验）
**最终状态**: published
