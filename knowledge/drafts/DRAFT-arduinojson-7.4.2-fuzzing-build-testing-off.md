# DRAFT: header-only CMake 库 conan create 中 fuzzing 目标链接 libclang_rt.fuzzer.a 与 OHOS libc++ ABI 不匹配（std::__h 符号缺失）

- **草稿**: DRAFT-arduinojson-7.4.2-fuzzing-build-testing-off
- **来源库**: arduinojson 7.4.2（bblanchon/ArduinoJson）
- **门禁**: conan-verify G2（conan create）
- **状态**: DRAFT — 需审核后 promote 为正式 E 条目

## 问题

header-only CMake INTERFACE 库（ArduinoJson 7.4.2）在 OHOS armv8 Conan 2.x 适配中，
`conan create` 的链接阶段失败：

```
ld.lld: error: undefined symbol: std::__h::ios_base::init(void*)
ld.lld: error: undefined symbol: std::__h::basic_streambuf<char, std::__h::char_traits<char>>::basic_streambuf()
ld.lld: error: undefined symbol: std::__h::basic_iostream<char, std::__h::char_traits<char>>::~basic_iostream()
ld.lld: error: too many errors emitted, stopping now
```

## 根因

CMake 顶层工程使用 `if(CMAKE_PROJECT_NAME STREQUAL PROJECT_NAME AND BUILD_TESTING)` 门控，
把上游测试套件与 `extras/fuzzing` 目录纳入默认构建。CTest 默认开启 `BUILD_TESTING`，
于是 `conan create` 构建 header-only 包时也编译 fuzzer 可执行文件；其链接的
`libclang_rt.fuzzer.a` 引用 `iostream/basic_ostream` 等符号，而 OHOS libc++ 使用
`std::__h` 内联命名空间且链接行未正确带上 libc++ 运行时，导致 ld.lld 报
`undefined symbol: std::__h::...` 系列错误。该失败与库本体源码无关，属于
OHOS 工具链 + 上游 fuzz 目标的装配问题。

## 方案

conanfile.py 的 `build()` 中显式关闭上游测试构建：

```python
def build(self):
    apply_conandata_patches(self)
    cmake = CMake(self)
    cmake.configure(variables={"BUILD_TESTING": "OFF"})
    cmake.build()
```

上游测试在适配阶段独立验证：`cmake --build build --target <Tests...>` +
`ctest --output-on-failure -E fuzzer`（排除 fuzzer 目标），结果如实记录在
`test_package/MANIFEST.yml`，不在配方中伪造通过。

## 验证

- arduinojson 7.4.2，OHOS armv8，clang 15.0.4，conan 2.29.1
- conan-verify G0-G4 + L2/L4/L5 全 PASS
- test_package 100% tests passed (1/1)
- 上游测试（ctest -E fuzzer）：27/27 通过

## 适用边界 / 限制

- 仅适用于构建阶段装配问题；若 fuzzer 链接失败伴随库自身源码错误，应先修源码。
- `BUILD_TESTING=OFF` 不替代上游测试验证；MANIFEST.yml 必须如实记录独立测试结果。
- 反例（禁止）：在 test_package 或配方中伪造 fuzzer/上游测试通过、把
  `BUILD_TESTING=ON` 写进 conan create 路径、未运行 fuzzer 却宣称其 PASS。

## 查重差异

已扫描官方只读快照 `knowledge/graph/E*.kv` 与 `knowledge/drafts/`：
- 无等价命中：无条目覆盖 `libclang_rt.fuzzer.a` / `std::__h` 符号缺失 /
  `BUILD_TESTING=OFF` 规避路径。
- 相邻条目 E092（CMake 不认识 HarmonyOS 平台）、E292（大型 C++ 库测试分层迁移）、
  E321（codeload URL 无扩展名）、DRAFT-ctre（header-only 配方 test_package 落地）、
  DRAFT-cmake-test-framework-fetch（Catch2 FetchContent 改造）均不覆盖本错误面。
- 本草稿聚焦 OHOS 特有的 fuzzer 运行时 ABI 装配失败与 conan 配方的标准规避动作，
  具跨库复用价值（所有带上游 fuzz 目录的 CMake C++ 库）。
