# DRAFT-valijson-1.1.3-ohos-float-from-chars-auto-fallback

## 问题 (Problem)

valijson 1.1.1 在 HarmonyOS PC (aarch64) 适配时，`std::from_chars` 浮点重载
（double）在 OHOS libcxx 不可用，需要两个补丁把 `std_string_adapter.hpp` 与
`internal/basic_adapter.hpp` 中的浮点 from_chars 替换为 `std::strtod`。
到 valijson 1.1.3 时上游已自行修复：新增 `internal/double_parser.hpp`，
在**编译期自动检测** `std::from_chars` 浮点支持并按需回退，OHOS 下无需任何补丁。

## 根因 (Root Cause)

1. OHOS SDK 的 libcxx（clang 15 工具链，`_LIBCPP_VERSION=15004`）`<charconv>`
   不提供浮点 `from_chars` 重载（float/double/long double），只有整型版本。
2. 上游按编译器版本（clang major > 13 / `_LIBCPP_VERSION >= 200000` /
   `_GLIBCXX_RELEASE >= 11`）判定浮点 from_chars 支持；OHOS libcxx 版本号
   未达阈值时能力宏为 0，走内置回退。

## 方案 (Solution)

valijson 1.1.3 的 `internal/double_parser.hpp` 提供三层回退链：

1. `VALIJSON_HAS_STD_FROM_CHARS` 编译期检测：
   `_MSC_VER>=1915` / `_LIBCPP_VERSION>=200000` / `_GLIBCXX_RELEASE>=11` → 用
   `std::from_chars`；
2. `VALIJSON_HAS_FAST_FLOAT_FROM_CHARS` 定义时 → 用 `fast_float::from_chars`；
3. 均不满足（OHOS 默认路径）→ `std::istringstream` 严格解析：
   `imbue(locale::classic()) + noskipws + (stream>>v) && peek()==eof`。

`parseDouble(const std::string&, double&)` 为唯一入口，`maybeDouble()/asDouble()`
经 `BasicAdapter`/`StdStringAdapter` 统一走该入口。**适配策略**：先检查上游
当前版本是否已内置自动回退（如本库 1.1.3），有则零补丁；无才考虑
bitserializer 式补丁（关闭能力宏 + strtod 回退）。

## 验证 (Verification)

- 上游测试全量：`./test_suite` → `187 tests / 185 PASS / 2 SKIP(上游自禁) / 0 FAIL`
  （thirdparty 按 v1.1.3 钉定 commit 还原）。
- 鸿蒙专项测试（`test_valijson_ohos.cpp`）：
  - `VALIJSON_HAS_STD_FROM_CHARS=0`（OHOS 工具链实测值），确认走 istringstream 回退；
  - 9 组合法输入（含 `"1e10"`、`"1.7976931348623157e308"`、
    `"0.30000000000000004"`、`"-0.0"`）解析正确；
  - 5 组非法输入（`"not-a-number"`、`""`、`"1.2.3"`、`"12abc"`、`" 1.5"`）全部拒绝；
  - RapidJson 适配器端到端 schema 校验（类型/数值越界/必填）全部通过，退出码 0。
- conan create（ohos-aarch64 profile）干净构建 + test_package 消费者编译运行通过。

## 适用边界 (Applicability)

- 触发条件：C++17 库在 OHOS aarch64 做字符串→浮点转换且依赖
  `std::from_chars` 浮点重载；OHOS libcxx 未达自动检测阈值。
- 适用：任意需要判断"上游是否已内置 from_chars 回退"的适配任务；
  istringstream 严格解析（noskipws + classic locale + 全串消费）可作通用回退模板。
- 不适用：仅使用整型 from_chars 的库；标准 libc++（浮点 from_chars 可用）环境。
- 反例：硬传 `std::chars_format` 重载给 OHOS libcxx 仍编译失败。

## 限制 (Limitations)

istringstream 回退速度低于 from_chars/fast_float；严格 `peek()==eof` 会拒绝
`" 1.5"` 等带空白输入（JSON 数值本就不允许空白，语义正确）；locale 必须
`classic()`，否则小数点受环境 locale 影响。
