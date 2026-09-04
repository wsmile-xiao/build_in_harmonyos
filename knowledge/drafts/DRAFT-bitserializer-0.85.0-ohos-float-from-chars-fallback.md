# DRAFT-bitserializer-0.85.0-ohos-float-from-chars-fallback

## 问题 (Problem)

bitserializer 0.85.0 在 HarmonyOS PC (aarch64) 上执行 `conan create`（test_package
消费者编译）时，浮点字符串转换路径报编译错误：

```
convert_fundamental.h:131:19: error: call to deleted function 'from_chars'
  validateResult(std::from_chars(it, end, out), in);
charconv:116:19: note: candidate function has been explicitly deleted
  from_chars_result from_chars(const char*, const char*, bool, int = 10) = delete;
charconv:783:1: note: candidate template ignored: requirement 'is_integral<double>::value'
  was not satisfied
```

库按编译器版本判断 `BITSERIALIZER_HAS_FLOAT_FROM_CHARS`（clang>13 → 1），但
OHOS SDK 26.0.0.18 的 libcxx-ohos `charconv` 只有整型 `from_chars`，
浮点重载（float/double/long double + chars_format）未实现。

## 根因 (Root Cause)

1. OHOS SDK 的 libcxx-ohos `charconv` 仅提供受 `is_integral` 约束的整型
   `from_chars`（3 参与 4 参 base 版）以及 `= delete` 的 bool 版本；
   浮点 `from_chars`（含 `chars_format` 参数形式）未实现，与上游标准 libc++ 不同。
2. 上游库用编译器版本（clang major > 13）而非目标平台 libc++ 能力判定
   浮点 from_chars 支持，OHOS 上被误判为可用，实例化时命中 deleted/约束模板。

## 方案 (Solution)

在配置头生成模板（`cmake/bitserializerConfig.h.in` → 生成 `config.h`）的能力宏判断中，
对 OHOS 工具链（`__OHOS__`）显式关闭浮点 from_chars：

```c
#if defined(__OHOS__)
#define BITSERIALIZER_HAS_FLOAT_FROM_CHARS 0
#else
// 原编译器版本判断
#endif
```

宏为 0 后，浮点字符串转换自动落入库内 `convert_compatibility.h` 的
strtod/strtof/strtold（+snprintf 格式化输出）回退路径；整型路径保持使用
`std::from_chars`。已固化为 `archives/b/bitserializer/0.85.0/patches/0001-cmake-bitserializerConfig.h.in.patch`，
conandata.yml 声明，`apply_conandata_patches` 在干净构建时自动应用。

## 验证 (Verification)

- `conan create`（ohos-aarch64 profile）干净构建 + test_package 消费者编译通过
  （test.cpp 做 string↔numeric 往返，含浮点 3.5）。
- 上游单元测试 860/860 通过（`ctest`，OHOS 本地）。
- conan-verify G0-G4/L2/L4/L5 全部通过。

## 适用边界 (Applicability)

- 触发条件：C++17 库在 OHOS aarch64 上调用 `std::from_chars` 浮点重载，
  且库头按编译器版本（而非平台 libc++ 能力）声明浮点 from_chars 支持。
- 不适用：仅使用整型 from_chars 的库；或目标平台为标准 libc++（浮点
  from_chars 可用）的环境。
- 反例：硬传 `std::chars_format::general` 给 from_chars 试图绕过——OHOS
  libcxx-ohos 无该重载，依旧编译失败。

## 限制 (Limitations)

浮点路径回退 strtod/snprintf 后，精度/格式与 from_chars 略有差异
（strtod 依赖当前 locale 的 decimal point；snprintf %g 输出位数不同），
对一般序列化场景可接受；要求严格 round-trip 的场景需在测试中显式覆盖。
