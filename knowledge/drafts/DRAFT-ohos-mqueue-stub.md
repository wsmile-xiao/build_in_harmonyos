# DRAFT-ohos-mqueue-stub — OHOS musl 补 POSIX 消息队列函数 stub

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-03
> **Severity**: 🟡 medium | **Category**: ohos / musl / mqueue / posix / compilation

## 相关既有条目（同族差异化定位）

本 skill 与既有 "musl libc 缺失" 条目共享 OHOS musl 兼容层背景，但本条目是
**整族 POSIX 消息队列函数缺失**——非重复条目；申报路径 B 时以此差异化定位为准。

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **E081**（secure_getenv） | 正式收录 | musl 无 secure_getenv（单个函数） | 非本题——那是**单个函数**且可降级 getenv；本条目是**整族 mq 函数**（mq_open/getattr/receive/unlink），OHOS 无 mqueue 运行时，只能 stub（ENOSYS） |
| **E493**（program_invocation_name） | 正式收录 | musl 无 glibc 符号 | 非本题——那是**数据符号**；本条目是**函数族** |
| **E085/E127**（pthread 取消族） | 正式收录 | musl 无 pthread_cancel 族 | 同族（函数族 stub ENOSYS），但**符号不同**——pthread 取消 vs POSIX 消息队列；触发库、错误特征、修法落点均不同 |
| **DRAFT-ohos-r34-static-lib-symbol-check**（asterisk-tds） | 草稿 | R34 静态库符号校验 | 非本题——那是**测试校验**；本条目是**编译期 stub** |

> 全库查证（2026-09-03）：`mq_open`/`mq_receive`/`mq_unlink`/`mq_getattr`/POSIX
> 消息队列 stub 命中 0 条——无正面撞车；本条目为真增量。

## Scope（何时用）

在 OHOS 上编译、使用 POSIX 消息队列接口（`mq_open`/`mq_getattr`/`mq_receive`/
`mq_unlink` 等）的库时，若出现：

- `call to undeclared function 'mq_getattr'`（sd-daemon.c 的 `sd_is_mq`）；
- `call to undeclared function 'mq_receive'`（socket-util.c）；
- `call to undeclared function 'mq_unlink'`（clean-ipc.c）；
- `call to undeclared function 'mq_open'`（core/socket.c）。

典型实例：systemd/261。

## Symptom

```text
sd-daemon.c:428: error: call to undeclared function 'mq_getattr'
socket-util.c:1212: error: call to undeclared function 'mq_receive'
clean-ipc.c:349: error: call to undeclared function 'mq_unlink'
```

## Root Cause

1. OHOS musl 的 `<mqueue.h>` 只定义 `struct mq_attr`（mq_flags/mq_maxmsg/
   mq_msgsize/mq_curmsgs）与 `mqd_t` 类型，**不声明**任何 POSIX 消息队列函数；
2. OHOS 无消息队列运行时；
3. 使用 mq 接口的库编译报 `call to undeclared function`（ISO C99 起隐式声明是错误）。

## Recommended Solution

**主方案：musl 兼容头补 mq_* 函数 stub。**

在 musl 兼容头（`src/include/musl/mqueue.h`）`include_next <mqueue.h>` 后补
`static inline` stub，返回 `-1` + `errno=ENOSYS`：

```c
static inline mqd_t mq_open(const char *name, int oflag, ...) {
        (void) name; (void) oflag; errno = ENOSYS; return (mqd_t) -1;
}
static inline int mq_getattr(mqd_t mqdes, struct mq_attr *attr) {
        (void) mqdes; (void) attr; errno = ENOSYS; return -1;
}
static inline ssize_t mq_receive(mqd_t mqdes, char *msg_ptr, size_t msg_len,
                                 unsigned int *msg_prio) {
        (void) mqdes; (void) msg_ptr; (void) msg_len; (void) msg_prio;
        errno = ENOSYS; return -1;
}
static inline int mq_unlink(const char *name) {
        (void) name; errno = ENOSYS; return -1;
}
```

调用方（如 `sd_is_mq` 的 `mq_getattr < 0` → 走 `-ENOSYS` 表示不支持）语义正确。

**回退方案**：若 stub 不可行，patch 源码绕开 mq 调用——改动面大，不推荐。

## 单库实证

| 库 | 角色 | 结果 |
|----|------|------|
| **systemd/261** | 主验证（本 PR） | ✅ 覆盖前 mq_getattr/mq_receive/mq_unlink/mq_open 系列报 undeclared；补 stub 后编译通过，conan create 通过 |

## 测试覆盖边界

- stub 只在 **OHOS 无 mqueue 运行时**下生效（返回 ENOSYS），不改有 mqueue 平台的
  行为；
- 声明通过率时：以 conan create 全流程（libsystemd.so.0.44.0 链接 + test_package
  R34）为实证；systemd 上游测试按 rule 1.2 平台限制声明（需运行中的 systemd 环境）。
