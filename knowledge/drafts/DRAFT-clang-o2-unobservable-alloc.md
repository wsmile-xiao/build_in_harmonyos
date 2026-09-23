# DRAFT-clang-o2-unobservable-alloc：clang -O2 消除不可观察分配导致 hook/分配器测试失败与 -fno-builtin 修复

> Contributor: oh-executor pc2-7 | Status: Draft | Updated: 2026-09-11
> Source: PR 【知识库扩展】feat(gperftools) perftools-1.6 R03 返工

## 背景

gperftools 1.6 的 tcmalloc 单元测试（tcmalloc_minimal_unittest / tcmalloc_unittest /
tcmalloc_both_unittest 及 debug 变体、system_alloc_unittest）在 OHOS 上批量 FAIL：
`Check failed: g_NewHook_calls > 0` 与 `Check failed: a.invoked_`。单独用独立
最小复现（hooknew2）验证 malloc/new/new[] 的 hook 均正常触发（g_new_calls=1/2/3），
证明 hook 机制本身无缺陷，差异在测试二进制编译环境。

## 根因

OHOS 工具链 clang-15 在 `-O2` 下对"不可观察分配"做消除优化：`new char[100]`
分配出的指针仅传给 `delete[]`、从未被观察或使用，编译器判定该
operator new/delete 配对无副作用可整体删除（allocator elision 语义），
`tc_newarray`/`tc_new` 不被调用 → `MallocHook::InvokeNewHook` 不执行 →
`g_NewHook_calls == 0` → 测试断言失败。system_alloc_unittest 的
自定义系统分配器钩子同理。诊断特征：单跑 hook 正常、二进制反汇编无
`bl tc_newarray`、heap 文件栈为空（`@` 后无地址）。

## 解决方案

在测试/构建配置的 AM_CXXFLAGS 补全全局 `-fno-builtin`（上游已有
`-fno-builtin-malloc/-fno-builtin-free/...` 系列，但缺 new/delete 项；
仅列 malloc 族不够，clang 仍可消除 operator new/delete 配对）：

```makefile
AM_CXXFLAGS += ... -fno-builtin-valloc -fno-builtin-pvalloc -fno-builtin
```

最小复现验证：`clang++ -O2` 下不观察的 `new char[100]; delete[] b;`
hook 计数 0；加 `-fno-builtin` 后计数恢复 1。修复后 hook 类 5 项 +
system_alloc 1 项全部转绿。属编译器优化语义差异，非库缺陷；
另一种等价修复是让测试观察分配指针（如打印或 CHECK 非空）。

## 适用边界

- 适用于通过 hook/分配器回调断言"分配确实发生"的测试被 -O2 优化消除的场景
- 不适用于库本体运行态问题；若测试已观察指针则无需此标志
- 全局 `-fno-builtin` 会禁止全部 builtin 优化（含 memcpy 等），仅建议用于测试编译标志

## 查重差异

- E293（C++17 动态异常规范/register）：不同主题，无冲突
- E026（glibc TLS 扩展 on musl）：不同主题，无冲突
- E002（/tmp 只读 set-env-var）：仅测试环境层面相关，机制不同
