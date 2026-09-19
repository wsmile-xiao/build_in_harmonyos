# E-DRAFT: C++17 移除构材以 `__cplusplus` 派生特征宏编译清除

- **触发实例**：libodb / libodb-pgsql 2.4.0 适配（2026-09，分支 feat/libodb-pgsql-2.4.0）
- **错误签名**：`error: no template named 'auto_ptr' in namespace 'std'` +
  `error: ISO C++17 does not allow dynamic exception specifications`
- **类别**：cxx17-migration（老 C++ 代码库 × C++17-only 平台）
- **严重度**：2（编译期确定性失败，修复手法范式化）

## 症状

C++17 下编译 libodb 2.4.0 核心头，共 20 个错误：

- ~14 × `no template named 'auto_ptr' in namespace 'std'`
  （connection.hxx / database.hxx / lazy-ptr.hxx / pointer-traits.hxx /
  wrapper-traits.hxx 及对应 .ixx）；
- 6 × `ISO C++17 does not allow dynamic exception specifications`
  （details/shared-ptr/base.hxx、operator new/delete 的 `throw(std::bad_alloc)` 等）。

`-std=c++14` 对照全部干净——构材是被 C++17 标准移除的，不是平台 bug。

## 根因

2010 年代及更早的 C++03/TR1 风格库大量使用 `std::auto_ptr` 与动态异常规范，二者均被
C++17 标准移除；而 OHOS SDK 的 libc++ 头只支持 ≥C++17（见 E130）。平台要求
`-std=c++17` 不可退让，降标准这条路在本平台被堵死，因此只能把移除构材
**条件编译清除**。

## 最小修复（平台无关、零平台宏）

在中心配置头派生特征宏——判断语言标准，不判断平台（R8 合规）：

```c
#if __cplusplus >= 201703L
#  define ODB_NO_AUTO_PTR
#endif
```

- `auto_ptr` 特化段用 `#ifndef ODB_NO_AUTO_PTR` 包裹；
- 动态异常规范直接删除，或以 `#if __cplusplus < 201703L` 守卫。

老标准下行为零变化，可上游化，同一手法可推广到任何 C++17 移除构材。libodb 2.4.0
清除 20 处后 C++17 全绿（patched exit=0；CI run2-7 携带补丁、L1 PASS）。

## 退路（有代价）

兼容 shim/别名头（自带一个 auto_ptr 替身）能救无法动库内头的场景，但那是掩盖兼容
缺口而非修复，语义与真实（已移除的）`std::auto_ptr` 不一致，仅作最后退路。

## 禁忌

- 禁止全局降 `-std=c++14`——SDK libc++ 头自身要求 C++17（E130 方向），错误只会
  换个地方爆炸；
- 禁止改 SDK 头恢复 auto_ptr；
- 禁止 `#ifdef __OHOS__` 一类平台宏守卫（R8 红线）。

## 适用范围与查重

- **适用**：一切前 C++11 代码库在 OHOS clang/libc++（或任何 C++17-only 环境）的
  迁移。修复策略排序：**特征宏清除 > shim > 降标准（本平台不可行）**。
- **证据**：独立探针 c++17 = 20 errors / c++14 = PASS_CLEAN / 补丁后 c++17 =
  PASS_CLEAN（curator/probe/probe_results.log）；本 run 定向验证 baseline exit=1 →
  patched exit=0（builder/verify/result_baseline_cxx17.txt、
  builder/verify/result_patched_cxx17.txt）。自包含复现：一行 TU（`std::auto_ptr` +
  `throw(X)`）c++17 必失败、c++14 干净，任意新 shell 可跑。
- **查重**：`grep -l -i 'dynamic exception' knowledge/graph/*.kv` 命中既有条目
  **E293**（2003 年代旧 C++ 代码在 C++17 下动态异常规范 `throw(...)` 与 `register`
  编译失败）——与本条主错误签名同族，如实引用并写明差异：
  - **覆盖面**：E293 仅 throw(X)+register，未覆盖 `std::auto_ptr`；
  - **解法**：E293 rec=toolchain-flag（`-Wno-error=dynamic-exception-spec` /
    `-Wno-error=register`）把诊断降级为 warning，无特征宏方案，其 fallback
    （`noexcept(false)` 替换）也非范式化清除；
  - **本条增量**：auto_ptr 特化段清除 + `__cplusplus` 派生特征宏编译清除范式
    （`grep -l -i auto_ptr knowledge/graph/*.kv` 零命中，E293 未覆盖）。
  - **结论**：同族不同解，互补不重复（similar_to 而非重复）。
  另 E130 同环境方向互补（E130 是"升 -std 解决头不兼容"，本条是"升完标准后清除
  已移除构材"），E198 为 C++ 标准演进废弃族近亲。
