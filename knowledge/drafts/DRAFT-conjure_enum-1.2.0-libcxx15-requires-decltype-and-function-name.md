# conjure_enum 1.2.0 — OHOS clang15/libc++15 requires-clause 成员探测与 function_name 反射兼容（draft）

**Category**: libcxx | toolchain | cpp20 | compile · **Severity**: 2 · **Tool**: clang++/cmake/conan

## 症状

1. 头文件内受限重载 `static constexpr int get_first() noexcept requires std::is_enum_v<decltype(T::ce_first)>`
   在 OHOS clang 15.0.4 上**硬报错** `no member named 'ce_first' in 'T'`（SFINAE 失效），而非静默使约束不满足；
   连锁触发 `constexpr variable 'enum_min_value' must be initialized by a constant expression` 与
   `conjure_enum requires non-empty enum`（valid_cnt==0）。
2. libcxx-ohos（`_LIBCPP_VERSION 15004`）缺失 `<source_location>` 头；当 polyfill 用
   `__builtin_FUNCTION()`（裸函数名，如 `epeek_builtin`）替代 `function_name()` 时，
   **解析 `source_location::function_name()` 提取模板实参的反射库会静默失效**——
   `conjure_enum` 依赖 `std::source_location::current().function_name()` 返回
   `epeek() [e = component::path]` 形态来解析枚举名，裸函数名导致全部值被判 invalid。

## 根因

- clang 15 对 requires-clause 内的 `decltype(T::member)` 求值不走可替换的 immediate context，
  对于不存在的成员直接 hard error（与目标无关的约束检查缺陷），而不是把约束判为不满足。
  用 `requires requires { T::ce_first; }` 括起来的 requires-expression 形式则能正确软失败。
- OHOS SDK 26（ohos-sdk_26.0.0.18）定制 libc++ 15.0.4 无 `<source_location>`（C++20 P0662，
  libc++ 于 LLVM 16 才落地）。常规 polyfill（`__builtin_FILE/LINE/FUNCTION`）只能提供
  file/line/裸函数名；对**解析 function_name() 文本提取模板实参**的反射库（如 conjure_enum、
  各类 enum/typename 反射库），必须保持与 clang 原生 `function_name()` 相同的
  `__PRETTY_FUNCTION__` 形态（`const char *epeek() [e = component::path]`），
  `__builtin_FUNCTION()` 的裸名会静默破坏解析逻辑（0 个 valid 条目）。

## 处置（可复用）

1. **requires-clause 成员探测**：把 requires-clause 内的 `decltype(T::member)` 探测改为
   `requires requires { T::member; }`：
   ```cpp
   static constexpr int get_first() noexcept requires requires { T::ce_first; }
       { return static_cast<int>(T::ce_first); }
   static constexpr int get_first() noexcept { return FIX8_CONJURE_ENUM_MIN_VALUE; }
   ```
   复现最小用例：clang15 下 `requires std::is_enum_v<decltype(T::ce_first)>` 硬报错，
   `requires requires { T::ce_first; }` 编译通过并正确选回退重载。
2. **function_name 反射 polyfill**：`__has_include(<source_location>)` 能力探测；
   缺失时在 `tpeek()/epeek()` 调用点直接 `return __PRETTY_FUNCTION__;`（clang 与原生
   `function_name()` 同形态，模板实参完整保留），不写 shim 类、不引入平台宏；
   工具链升级自动切回原生 `<source_location>`。
3. `<format>` 头存在但 `__cpp_lib_format` 符号缺失的同类缺口：`to_hex_string()` 等使用点
   守卫必须是 `defined(__cpp_lib_format) && __has_include(<format>)`，仅 `__has_include(<format>)`
   不够（头存在但实现整体被 `_LIBCPP_HAS_NO_INCOMPLETE_FORMAT` 关闭）。

## 验证

- clang++ -std=c++20 -fsyntax-only 最小复现：requires-clause 两形式对比通过；
- CMake 全量构建（含 srcloctest/example/statictest/cbenchmark）exit 0；
- 上游 Catch2 测试：ctest 51/51，本机运行 unittests（247 断言/41 用例）+ edgetests（25 断言/10 用例）全过；
- conan-verify G1-G4 全 PASS，test_package 真实 API 调用（conjure_enum/conjure_type/enum_bitset）运行通过；
- W3 本地 CI（build_and_test.sh）pass。

## 适用边界

适用于所有目标 OHOS clang15/libc++15 且使用：
（a）requires-clause 内 `decltype(T::member)` 做成员探测的 C++20 库；
（b）解析 `std::source_location::function_name()` 输出提取模板实参/枚举名的反射库；
（c）`<format>` 头存在但 `__cpp_lib_format` 未定义时需条件编译的库。
头文件缺失类问题对任意 OHOS 库通用（非本包特例），命中既有条目（E130 家族、
DRAFT-libfork/jsonifier/reflect-cpp/openrct2）时走等价复用，本条目仅新增上述两个无覆盖差异点。

## 反例与限制

- 不适用：clang16+/libc++16+（`<source_location>` 原生存在，`__PRETTY_FUNCTION__` 回退分支不激活）；
  非解析型使用（仅需 file/line）的库可用 `__builtin_FILE/LINE` 简易 polyfill，无需本方案。
- `__PRETTY_FUNCTION__` 是 clang/GCC 扩展（非 MSVC），MSVC 分支需另用 `__FUNCSIG__` 或原生特性宏。
- 不得在 patches 中引入 `__OHOS__` 平台宏（R8/PF5）；本方案全部为 `__has_include`/标准特性宏驱动。