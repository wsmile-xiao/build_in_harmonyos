# DRAFT-libshrinkwrap-1.2.0：头文件使用 std::uint8_t 却不 include <cstdint>（libc++ 传递包含掩盖）

> Status: **Draft**（待审核 promote）| severity: `P2` | category: `portability` | Updated: 2026-09-27
> 对应: `knowledge/drafts/DRAFT-libshrinkwrap-1.2.0-headers-rely-on-transitive-cstdint-libcxx.kv`

---

**匹配关键词**：uint8_t is not a member of std, cstdint, libc++, libstdc++, header-only

## 错误签名（error_signature）

```text
error: 'uint8_t' is not a member of 'std'; did you mean 'wint_t'?
```

## 错误摘录（error_excerpt）

```text
/probe/shrinkwrap-1.2.0/include/shrinkwrap/xz.hpp:323:23: error: 'uint8_t' is not a member of 'std'; did you mean 'wint_t'?
  323 |       std::array<std::uint8_t, LZMA_STREAM_HEADER_SIZE> stream_header_;
```

## 根因（root_cause）

shrinkwrap 1.2.0 的 5 个头文件（gz/istream/stdio/xz/zstd.hpp）大量使用
`std::uint8_t` / `std::uint64_t`，但只 include 了 `<array>/<vector>/<cstdio>/<iostream>`
等，从不 include `<cstdint>`。libc++（OHOS NDK 的 C++ 标准库）经由这些头文件
传递引入 `<cstdint>`，所以 OHOS aarch64 交叉编译（SDK clang 15 + libc++）能通过；
libstdc++（g++ 13 / Ubuntu 24.04）没有同等传递包含，同一个 TU 直接编译失败。
属于"依赖传递包含"（transitive include）反模式：换标准库实现即暴露。

## 推荐方案（rec_approach）

- OHOS 本身不受影响（libc++），本库 OHOS 适配不需要补丁（零补丁交付）。
- 在 libstdc++ 环境做等价验证时用 `g++ -include cstdint` 绕过，不改上游源码。
- 根治方案（可直接上游）：5 个头文件各加 `#include <cstdint>`（IWYU 原则，
  P005 通用可移植性）。
- 识别信号：同一份代码 clang/libc++ 过、g++/libstdc++ 挂，且错误落在
  `std::uintN_t`/`std::intN_t` 类型名上 → 先怀疑缺 `<cstdint>`。

---

*来源：libshrinkwrap 1.2.0 适配 W4 本机验证（Docker x86_64 Ubuntu 24.04 g++ 13
原生编译失败 → `-include cstdint` 后上游 11/11 通过；OHOS 交叉编译无需此修复）；
内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
