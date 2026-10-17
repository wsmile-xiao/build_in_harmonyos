# DRAFT: CMake 链接驱动语言由目标源文件决定，project(C CXX) 不能让纯 C 目标带上 C++ 运行时

## 错误特征
```
undefined symbol: __cxa_guard_acquire|__cxa_guard_release|__cxa_guard_abort
undefined symbol: operator delete(void*)|operator new(unsigned long)
undefined symbol: vtable for __cxxabiv1::__vmi_class_type_info|std::terminate()
test_package C 源文件消费 C++ 实现的静态库时 C 驱动链接失败
```

## 根因分析
CMake 为可执行目标选择链接命令（CMAKE_<LANG>_LINK_EXECUTABLE）时，
依据的是**目标源文件的语言集合**，而不是 project() 声明。一个纯 .c
目标即使工程声明了 `project(x C CXX)`，仍由 C 驱动（clang，非 clang++）
链接——不会自动追加 libc++/libc++abi。当被消费的静态库是 C++ 实现
（如 ICU、许多 C API 包 C++ core 的库）时，链接期报 C++ 运行时符号未定义。
`enable_language(CXX)`、给 target 加 CXX_STANDARD、在 conanfile 设置
compiler.libcxx 均无效，因为问题在链接驱动层。

本地实测（OHOS aarch64 clang-15）：
- `clang` 驱动链接 test.c + libicuuc.a：19 个 undefined symbol（CI 失败路径复现）
- `clang++` 驱动链接同一 API 的 test.cpp：链接成功、运行 9/9 断言通过

## 推荐方案
**方法**: rename-consumer-test-source-to-cpp

**说明**: 让 test_package 至少有一个 .cpp 源文件（内容仍可只调用被测包
C API，改动几乎为零），使目标由 clang++ 驱动链接并自动带上 C++ 运行时。
同步更新 CMakeLists.txt 的 add_executable 与 MANIFEST.yml 的文件名。
替代方案（不推荐）：手动 `set_property(TARGET t PROPERTY LINKER_LANGUAGE CXX)`
——同样有效但语义生硬；`target_link_libraries(t PRIVATE c++ c++abi)`
依赖运行时库名，跨工具链脆弱。

## 验证/命令
```
# 失败路径复现（应报 undefined __cxa_*）:
clang -I<pkg>/include test.c <pkg>/lib/libicu*.a -lm
# 修复路径验证（应 0 错误且运行通过）:
clang++ -std=c++17 -I<pkg>/include test.cpp <pkg>/lib/libicu*.a -lm && ./a.out
```

## 关键词
CMake, link driver language, LINKER_LANGUAGE, clang, clang++, libc++,
libc++abi, __cxa_guard, operator delete, vtable, test_package, static library,
C API C++ implementation, project C CXX 无效

## 来源
- PR #8988 (icu/76.1)，CI 构建 b54819 (#48115) / b55279 (#48537) 两次同因失败，
  b55861 (#48876) test.c→test.cpp 后通过
- 上一个提交 171cef10 仅加 project(C CXX)，CI 仍红——证明声明层面修复无效

TODO: 状态、严重度评定，评审后转正式 E-entry
