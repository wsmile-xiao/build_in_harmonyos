# DRAFT：头文件内部 `using namespace` 让 API 看似成员、实为全局——限定名调用编译失败

> Contributor: CIW | Status: Draft | Updated: 2026-09-21
> Source: sz 3.3.2 适配（PR #11675，test_package/test_sz.cpp）
> 同 stem 知识文件：`DRAFT-sz-3.3.2-namespace-qualified-call-global-symbol.kv`

## 错误特征

消费者测试按"看起来像成员"的写法调用：

```cpp
SZ3::SZ_compress(...);   // error: no template named 'SZ_compress' in namespace 'SZ3'
```

而同一符号**非限定调用就能编译通过** —— 说明它根本不在 `SZ3` 里。

## 根因分析

上游头文件内部有 `using namespace SZ3;`（或 `using SZ3::foo;`），把名字**注入全局**：
符号在全局可见，但在 `SZ3` 下**没有以限定名声明**。
sz 实测：`sz.hpp` 内 `using namespace SZ3`，`SZ_compress/SZ_decompress` 实为**全局函数**。

## 推荐方案

**方法**: verify-real-qualification-then-use-unqualified-name

```bash
grep -n 'using namespace' include/*.hpp | head           # 看是否只是 using 注入
nm -C build/*.a | grep -m3 'SZ_compress'                 # 用 mangled 名确证真实命名空间
```

①**确证真实限定**（头文件定义处 / `nm -C` 符号名）；②按真实限定调用——真在全局就用**非限定名**；
③**不得**改库、加 shim 或 `#define` 掩盖。

## 适用范围与反例

- **适用**：C++ 库的 `test_package`；上游头文件大量用 `using namespace X;` 时。
- **判据**：报错为 `no template named / no member named ... in namespace ...`，**去掉限定符即可编译**。
- **反例/边界**：
  - 与 **`using namespace std;` 引起二义性（ambiguous）** 的条目（如 farmhash）**不同**：本条是**限定名不存在**；
  - 若符号在 libc++/musl 下确实缺失，属另一类问题，勿混入；
  - 调用方式应与上游文档示例一致，文档缺失才以探针为准。

## 验证证据（sz 3.3.2 / PR #11675）

- 初版消费者测试：`SZ3::SZ_compress(...)` → `error: no template named 'SZ_compress' in namespace 'SZ3'`；
- `notes.md` 第 44 行原文：`消费者测试 SZ3::SZ_compress 报 no template | 根因：SZ_compress/SZ_decompress 是全局函数（sz.hpp 内部 using namespace SZ3），非 SZ3::`；
- 改为非限定调用后：消费者测试 **1/1 passed**（`N=65536 float`、`absErrorBound=0.1`、断言 `maxErr≤bound`）。

## 与既有条目的差异（查重结论）

- KB 中 `using namespace` 命中 **farmhash（`using namespace std` 二义性）**、bitserializer（传递包含）、E2175（libc++/libstdc++ 宽严差异）、E429（非限定符宏展开）——
  **均非"限定名不存在"** 这一签名 ⇒ 按 **create** 申报（`similar_to: DRAFT-farmhash-1.1.0-cxx17-std-data-ambiguity` 作家族关联）。
