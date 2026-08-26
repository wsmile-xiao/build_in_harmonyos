# authselect 1.7.1 qsort_r OHOS musl libc 兼容性修复

## 问题

authselect 1.7.1 在 OHOS (OpenHarmony) 目标上构建时，`src/cli/authselect` 链接阶段失败：

```
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: qsort_r
>>> referenced by ../../src/lib/.libs/libauthselect.so
```

## 根因

authselect 内部 `src/lib/util/dir.c` 使用 glibc 风格的 `qsort_r` 函数对目录条目按 ctime 排序：

```c
qsort_r(items, string_array_count(items), sizeof(char *),
        sort_by_ctime, &dirfd);
```

其中 `sort_by_ctime(const void *a, const void *b, void *arg)` 是带用户上下文（`&dirfd`）的回调函数。

OHOS 使用 musl libc，其导出的是 BSD 风格的 `qsort_r`（参数顺序不同：`thunk` 在 `compar` 前面，且 `compar` 回调签名也不同），且 musl 的 `qsort_r` 未被 libc 导出到可链接符号（GNU 风格的 `qsort_r` 在 musl 上不存在）。

参见 `knowledge/musl-glibc-developer-impact.md` §2.3.3：glibc 与 musl 的 `qsort_r` 签名不兼容，ABI 与代码级均不兼容，直接替换会编译错误。

## 修复方案

在 `src/lib/util/dir.c` 中，以 `#ifndef __GLIBC__` 条件编译添加本地 `qsort_r` shim：

```c
#ifndef __GLIBC__
static int (*_authselect_qsort_r_compar)(const void *, const void *, void *);
static void *_authselect_qsort_r_arg;
static int _authselect_qsort_r_wrap(const void *a, const void *b) {
    return _authselect_qsort_r_compar(a, b, _authselect_qsort_r_arg);
}
static void qsort_r(void *base, size_t nmemb, size_t size,
                    int (*compar)(const void *, const void *, void *),
                    void *arg) {
    _authselect_qsort_r_compar = compar;
    _authselect_qsort_r_arg = arg;
    qsort(base, nmemb, size, _authselect_qsort_r_wrap);
}
#endif
```

该 shim 通过静态全局变量保存比较器上下文，再委托给标准 `qsort`。由于 authselect 是单线程 CLI 工具，静态上下文是安全的。

## 验证

- 编译：`src/lib` 完整编译通过（`libauthselect.a` 生成），`src/cli/authselect` 链接成功（无 `qsort_r` 未定义错误）
- 单元测试：`make check` 3 个 cmocka 测试全部通过（PASS: test_util_string_array, test_util_evaluator, test_util_template）
- 排序行为：`sort_by_ctime` 回调通过 `_authselect_qsort_r_wrap` 间接调用，排序行为与原始 glibc `qsort_r` 一致（委托给标准 `qsort`，仅上下文传递方式不同）

## 适用边界

- 仅适用于 **OHOS (musl libc) 目标**，glibc 目标通过 `#ifndef __GLIBC__` 条件编译跳过
- 仅适用于 **单线程场景**：静态上下文变量在并发调用 `qsort_r` 时存在竞态条件
- authselect 是 CLI 工具（单线程），修复安全
- 若其他多线程应用遇到相同问题，需改用线程局部存储（`_Thread_local`）或完全重入实现

## 与 glibc/musl qsort_r 差异的关系

musl-glibc-developer-impact.md §2.3.3 记录了两种 `qsort_r` 签名差异：

| 签名 | glibc (GNU) | musl/OHOS (BSD) |
|------|-------------|-----------------|
| 函数原型 | `qsort_r(base, n, size, compar, arg)` | `qsort_r(base, n, size, thunk, compar)` |
| compar 签名 | `int compar(const void*, const void*, void*)` | `int compar(void*, const void*, const void*)` |
| 上下文位置 | 第四参数 | 第三参数（thunk） |
| OHOS 可用性 | ❌ 不存在 | ⚠️ 存在但与 GNU 签名不同 |

authselect 使用的是 GNU 签名。本修复不通过 musl 的 BSD 签名 `qsort_r`，而是提供本地 GNU 兼容 shim 委托给标准 `qsort`，从根本上避免了跨平台签名问题。

## 查重结果

| 来源 | 命中 | 关联 |
|------|------|------|
| knowledge/ (kv + md) | 8 命中 | musl-glibc 差异文档，非 authselect 专用方案 |
| knowledge/drafts/ | 0 | 无 authselect 相关既有草稿 |
| knowledge/graph/ | 0 | 无 E 条目直接覆盖 |
| 仓库内其他库 | 0 | 未发现其他库有相同 qsort_r 修复 |

## 非适用范围

- 非 OHOS 目标（glibc/Linux）不需要此修复
- 非 `qsort_r` 使用场景（如已使用 `qsort` 或其他排序函数）不需要
- 多线程/并发调用 `qsort_r` 的环境需要使用更安全的上下文方案（`_Thread_local` 或完全重入实现）

## 作者

- oh-bit (OHPC 执行端)
- 来源：authselect 1.7.1 OHOS R13 适配
- 状态：DRAFT