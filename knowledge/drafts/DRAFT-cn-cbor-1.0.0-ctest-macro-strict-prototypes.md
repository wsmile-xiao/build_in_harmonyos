# DRAFT-cn-cbor-1.0.0-ctest-macro-strict-prototypes: 测试框架宏生成无原型声明 + clang 15 `-Werror` → 配方层关上游 `fatal_warnings` 选项（零源码补丁）

> **Contributor**: pc1-49 | **Status**: Draft（pending editor review）| **Updated**: 2026-09-22
> **Source**: cn-cbor 1.0.0 HarmonyOS PC 适配（build_in_harmonyos，archives/c/cn-cbor/1.0.0）
> **拟提升编号：由知识库主编确认** —— 本草稿为未提升草稿，尚未分配正式 E 编号

## 场景

把使用轻量 C 测试框架头（ctest.h 类，`CTEST(suite, name)` 注册宏）的 C 库搬到
OHOS PC（clang 15.0.4 + musl）。上游 CMakeLists 暴露 `fatal_warnings` 选项且
默认 ON（对 GCC/Clang 追加 `-Werror`）。库本体源码为现代原型声明，编译正常；
但测试目标中测试框架宏展开出的 C89 风格无原型声明
`void __FNAME(sname, tname)();` 触发 clang 15 的 `-Wstrict-prototypes` 弃用
警告，被 `-Werror` 升级为错误，`cbor_test` 编译失败。

## 问题

可复用问题签名（日志症状）：

```text
error: a function declaration without a prototype is deprecated in all
       versions of C [-Werror,-Wstrict-prototypes]
fatal error: too many errors emitted
```

真实证据（cn-cbor 1.0.0，`test/ctest.h`）：

```c
#define CTEST(sname, tname) __CTEST_INTERNAL(sname, tname, 0)
#define __CTEST_INTERNAL(sname, tname, st) \
    void __FNAME(sname, tname)();          /* ← 无原型声明 */
```

上游 `test/CMakeLists.txt` 经 `create_test(cbor)` 将 `cbor_test.c` 编为可执行
并注册 CTest `cbor`；主 `CMakeLists.txt` 在 `fatal_warnings=ON` 时
`add_definitions(-Werror)`（GCC/Clang 分支），clang 15 将 strict-prototypes
警告升级为错误 → `make[2]: *** Error 1`，`fatal error: too many errors emitted`。

## 根因 (Root Cause)

1. ctest.h 类测试框架用宏展开生成无原型（empty parameter list）的测试函数
   声明，C89 风格；clang 15 起 `-Wstrict-prototypes` 默认开启并标注为
   "deprecated in all versions of C"。
2. 上游 CMakeLists 暴露 `fatal_warnings` 选项（默认 ON），对 GCC/Clang
   追加 `-Werror`，把上述弃用警告升级为编译错误。
3. 失败仅发生在**测试目标**；库本体源码（现代原型声明）不受影响——这解释了
   为什么 `conan create` 在库构建阶段正常却卡在测试目标。

## 方案 (Solution)

Conan 配方 `generate()` 关闭上游暴露的 `fatal_warnings` 选项（仅解除 -Werror
升级，测试编译警告照常输出但不阻断）：

```python
def generate(self):
    tc = CMakeToolchain(self)
    tc.variables["fatal_warnings"] = "OFF"
    tc.generate()
```

本地直编等价：`cmake .. -Dfatal_warnings=OFF && make && ctest`。
无需修改测试框架头、测试源码，无需补丁（区别于 DRAFT-asmotor 的 K&R 老源码
场景——那里必须源码级 `-Wno-strict-prototypes`）。

## 验证 (Verification)

本机即 HarmonyOS aarch64（clang 15.0.4，CMake 4.1.2，Conan 2.29.1）：

- **复现**: `cmake -Dfatal_warnings=ON(默认) .. && make` → `-Werror,-Wstrict-prototypes`
  20 errors，`cbor_test` 编译失败（exit 1）
- **修复后**: `cmake -Dfatal_warnings=OFF .. && make -j4` → 0 errors，
  `cbor_test` 链接成功（exit 0）
- **测试实跑**: `ctest --output-on-failure` 1/1 通过；`./dist/test/cbor_test`
  → `RESULTS: 11 tests (11 ok, 0 failed, 0 skipped)`（exit 0）
- **G2 复验**: `conan create`（ohos-aarch64 profile）→ G2 PASS，
  test_package 消费者测试（编解码往返 7 项断言）实际运行通过

## 适用边界 (Boundary)

- 适用：使用 ctest.h 类“宏生成无原型声明”测试框架、且 CMake 暴露
  fatal_warnings（或等价 -Werror 开关）的 C 项目，clang 15+ / OHOS / Linux；
  配方级选项形态（零源码补丁）
- 不适用：K&R 手写老源码无原型声明（→ DRAFT-asmotor，需
  `-Wno-strict-prototypes`）；无 fatal_warnings 选项的上游（→ E063，
  `-Wno-error=<class>` 逐个禁用类别）
- 反例边界：若上游把 `-Werror` 直接写死在 CMakeLists（无选项开关），则
  fatal_warnings=OFF 无效，须走 E063 类 `CMAKE_C_FLAGS` 注入
  `-Wno-error=strict-prototypes`

## 查重差异 (vs Existing)

| 条目 | 覆盖 | 差异 |
|------|------|------|
| E063（-Werror 级联，add-cflags-disable-werror） | 一般 -Werror 升级方案（Makefile `-Wno-error=xxx`） | 本候选=测试框架宏触发源 + 上游显式选项 fatal_warnings（CMake 变量注入，非 CFLAGS 追加） |
| DRAFT-asmotor-knr-strict-prototypes-c99 | K&R 老源码无原型 + -Werror → 源码级 `-Wno-strict-prototypes` | 本候选=宏展开声明（非手写源码）+ 配方级选项（零源码修改）；测试目标独占失败面 |

**查重结论**: combination_novelty=true、boundary_novelty=true（测试框架宏 ×
上游 fatal_warnings 选项 × 配方级注入点，既有条目未覆盖）；causal/trigger/
solution 三轴部分重叠。本候选为新增差异且已由 cn-cbor 1.0.0 真实日志双向
验证（复现/修复/测试/ G2），可跨库复用 → 建议提升为正式 E 条目（主编审核）。