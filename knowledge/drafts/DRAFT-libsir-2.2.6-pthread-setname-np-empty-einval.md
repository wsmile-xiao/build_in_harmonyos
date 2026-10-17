# DRAFT-libsir-2.2.6-pthread-setname-np-empty-einval

> Source event: `libsir/2.2.6` 上游测试 sanity-thread-ids（2026-09-27）。
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## 问题

libsir 上游测试 `sanity-thread-ids` 在"clearing thread name"步骤失败：

```text
!! Unexpected (23, Error in _sir_setthreadname (sirinternal.c:1389): 'Platform error code 22: Invalid argument')
```

库代码用 `_sir_setthreadname("")` 清空线程名，底层调用 `pthread_setname_np(
pthread_self(), "")`，在 OHOS 上返回 EINVAL (22)。

## 根因

glibc 的 `pthread_setname_np` 允许空字符串（把线程名清空）；OHOS 使用的
musl 系 libc 对空字符串返回 EINVAL。平台 libc 行为差异导致依赖"传空串清空
线程名"的上游库在 OHOS 上运行失败。

本机实测：

```text
set 'mythread': r=0 errno=0
set '':        r=22 errno=22 (Invalid argument)
current name:  'mythread'   # 空名未生效
```

## 解决方案

在调用 pthread_setname_np 前对空名字做 no-op 成功守卫（无平台宏，glibc/musl 兼容）：

```c
bool _sir_setthreadname(const char* name) {
    if (!_sir_validptr(name))
        return false;
    /* empty name: no-op; some libc (OHOS/musl) reject pthread_setname_np("") with EINVAL */
    if (0 == name[0])
        return true;
    ...
}
```

已固化为 `patches/0001-src-sirinternal.c.patch`（+6/-0）。

## 验证

- 修复前：`sanity-thread-ids` FAIL（36 项中 1 项失败）。
- 修复后：`./build/bin/sirtests` 36/36 全部 PASS；conan-verify G1-G4 PASS。

## 适用边界

- 适用：OHOS/musl 上通过 `pthread_setname_np` 设置/清空线程名的 C/C++ 库及其测试。
- 反例：常规 Linux/glibc 环境无此差异，无需该守卫（但守卫本身无害）。

## 限制

- no-op 守卫意味着"清空"不真正清掉线程名（保持旧名），对依赖线程名清空后
  展示变化的场景不适用；libsir 日志场景仅按线程名检索，行为等价。
- 关联知识：E202（musl PTHREAD_KEYS_MAX 差异）、E085/E127（OHOS pthread 面差异）
  同属 OHOS/musl 与 glibc 的线程 API 行为差异族。
