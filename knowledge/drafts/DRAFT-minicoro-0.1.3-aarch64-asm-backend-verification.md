# DRAFT-minicoro-0.1.3-aarch64-asm-backend-verification — 单文件协程/上下文切换库的 aarch64 汇编后端自动选择与 OHOS 专项验证

> **Contributor**: pc1-49 | **Status**: DRAFT | **Updated**: 2026-09-18
> **Severity**: medium | **Category**: ohos / headers / conan / testing / assembly
> **Audience**: 适配单头文件协程/上下文切换类 C/C++ 库（minicoro、boost.context 类、libco 类、ucontext 封装类）到 OpenHarmony/HarmonyOS aarch64 的执行端

## 问题签名与触发条件

场景：单文件协程库在 OHOS aarch64 的适配**没有编译错误**，但默认只跑普通消费者 API 冒烟
（test.c），不验证实现后端选择。风险是：头文件按架构宏自动选择后端
（`__aarch64__` → `MCO_USE_ASM` 汇编；其他平台回退 ucontext/fibers），如果专项测试
不做编译期断言，就无法证明 aarch64 汇编路径（而非回退路径）实际生效，适配完整性
（R40 类）未闭环。

触发条件：

```text
单头文件库（#define XXX_IMPL 单翻译单元实现）
+ 目标平台 aarch64-linux-ohos
+ 头文件含 __aarch64__ / MCO_USE_ASM 类架构宏分支
+ 专项测试缺少后端选择断言
```

## 真实适配事实（minicoro 0.1.3）

- minicoro v0.1.3 为单头文件非对称栈式协程库，header-only 适配**零源码补丁**：
  aarch64 命中 `minicoro.h` 的 `__aarch64__` 汇编实现（第 ~1081 行 MCO_USE_ASM）。
- 配方 `package_type="header-library"`，仅安装 `include/minicoro.h` + LICENSE；
  消费者在**且仅在一个翻译单元** `#define MINICORO_IMPL` 后 include。
- 鸿蒙专项测试 `test_ohos_platform.c`：
  - 编译期断言：`__aarch64__ && __linux__` 下 `MCO_USE_ASM` 被定义；
  - 运行期验证：嵌套协程（协程内创建/resume 另一协程）、深度 C 调用链（5 层）
    后 yield、自定义分配器（malloc_cb/free_cb 挂钩与分配/释放计数平衡）；
  - 结果：编译零警告，运行 `OHOS impl: MCO_USE_ASM (aarch64 assembly context
    switch)` + `15 assertions passed`，RUN_EXIT=0。

## 根因

单文件上下文切换库按架构宏选择汇编后端是上游设计，OHOS aarch64 下自动命中
`MCO_USE_ASM`，无需补丁；但“无需补丁”不等于“已验证”。后端选择验证缺失时，
适配证明不完整（与 R40「深度适配库需验证适配完整性」同族：编译通过 ≠ 适配完成）。

## 推荐方案

**方法**: single-tu-impl-header-library-plus-backend-assert-ohos-test

1. **配方结构**复用既有 header-only 条目（E257 no-op build 满足 G1、
   E321/E322/E470 header-library + cmake_file_name/target_name + test_package）；
2. **新增**：专项测试编译期断言后端宏被正确选择
   （`#if defined(__aarch64__) && defined(__linux__)` → 断言 `MCO_USE_ASM`）；
3. **运行期**验证嵌套协程 / 深调用链 yield / 自定义分配器语义；
4. 自定义分配器回调**签名必须与头文件声明逐字一致**
   （`malloc_cb(size_t size, void* allocator_data)` /
   `free_cb(void* ptr, void* allocator_data)`），避免参数顺序侥幸。

验证命令：

```bash
/data/service/hnp/bin/clang -Og -std=c99 -Wall -Wextra -I. test_ohos_platform.c -o test_ohos_platform
./test_ohos_platform
```

## 兜底方案

若头文件在目标架构无汇编分支而回退 ucontext/fibers：专项测试改为断言回退后端
可正常嵌套 resume/yield（行为正确性），并用上游 benchmark 记录
switch/init/uninit cycles 平台特征。

## 禁用项

- 编译期只写文字不 assert 的“伪后端断言”；
- 空壳专项测试（只 print 不调用 API，违反 R34）；
- 把样例/基准当独立上游用例充数（双口径规则）；
- 自定义分配器回调签名与头文件不一致仍报通过（ABI 侥幸）。

## 关联

similar_to: E257 / E321 / E322 / E470（header-only 配方结构）
原则: R34（test 必须实质依赖被测包）、R40（深度适配完整性）、R51（上游测试三步法）
来源: minicoro/0.1.3 适配（pc1-49, 2026-09-18）
