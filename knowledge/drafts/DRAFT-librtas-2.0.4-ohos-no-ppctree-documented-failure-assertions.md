# DRAFT-librtas-2.0.4-ohos-no-ppctree-documented-failure-assertions

> 缺平台能力时如何写不脆弱的测试：断言文档化失败集合 + 摸清返回值契约与位域归属
> 来源：librtas 2.0.4 适配
> 状态：草稿，待主编审核

## 背景

被测库在目标平台缺少底层能力（外架构 syscall、无 `/proc` 节点）时，
`test_package` 仍然必须过 CI `L0d` / `L1e` 与 `R34` 门禁：
**真实执行、真实断言、不能是空壳**。

这条给出两条可复用的踩坑规律。

## 规律一：返回值契约不是「0 = 成功」

`rtas_print_event()` 被误当成状态码：

```c
/* print_rtas_event.c */
int rtas_print_event(FILE *stream, struct rtas_event *re, int verbosity)
{
    int len = 0;
    if ((stream == NULL) || (re == NULL)) { errno = EFAULT; return 0; }
    len += print_scn_title("RTAS Event Dump Begin");
    for (shdr = re->event_scns; shdr; shdr = shdr->next)
        len += rtas_print_scn(stream, shdr, verbosity);
    len += print_scn_title("RTAS Event Dump End");
    return len;                      /* ← 累计打印字符数，不是状态码 */
}
```

首版 test 写 `rtas_print_event(...) == 0` → **1 条断言失败，conan create exit 1**。

**做法**：写任何 `返回值 == X` 断言前先读实现。计数型返回值断言 `> 0`，
再单独断言错误路径的 0：

```c
check(rtas_print_event(stdout, re, 0) > 0, "reports a positive character count");
check(rtas_print_event(NULL,      re, 0) == 0, "rejects a NULL stream with EFAULT");
```

## 规律二：失败码可能依调用者身份而变

```c
/* syscall_calls.c */
int sanity_check(void)
{
    if (geteuid() != (uid_t)0) return RTAS_PERM;        /* -1003 */
    if (!interface_exists())     return RTAS_KERNEL_INT; /* -1001 */
    return 0;
}
```

CI worker 可能以非 root 运行。硬编码 `-1001` 会在 root 机器上偶发红。

**做法**：断言「非 0 **且**落在库自有文档化错误集合内」——
既对 root / 非 root 都稳健，又如实断言真实行为（不把失败当成功）：

```c
check(rc != 0, "rtas_get_time() fails without an RTAS kernel interface");
check(rc == RTAS_PERM || rc == RTAS_KERNEL_INT,
      "rtas_get_time() returns a documented librtas error code");
```

## 规律三（附带）：位域归属要照实现写

```c
/* get_rtas_event.c: parse_re_hdr() */
re_hdr->severity    = (rawhdr->data1 & 0xE0) >> 5;
re_hdr->disposition = (rawhdr->data1 & 0x1C) >> 3;
re_hdr->extended    = (rawhdr->data1 & 0x04) >> 2;   /* ← 在 data1，不在 type */
re_hdr->initiator   = (rawhdr->data2 & 0xF0) >> 4;
re_hdr->target      =  rawhdr->data2 & 0x0F;
re_hdr->type        =  rawhdr->type;
```

首版注释把 `extended` 归给 `type` / `data2`。`data1=0` 时恰好正确，
但一旦为了「让 severity 非 0」而改 `data1` 的取值，就可能误置 `extended` 位，
走进 extended-header 解析分支 —— 而那条路径要求缓冲区里有合法的扩展头，
否则 `parse_rtas_event()` 失败、`event_length` 与节链表断言随之变红
（本例实测：把 `data1` 置成 `0x1C` 即置位 `extended` 后，3 条断言失败、
`conan create` exit 1；未观察到崩溃）。

**做法**：逐位对照移位表达式设置 fixture，并把 `data1` 设成非 0 severity
（`RTAS_HDR_SEV_ERROR << 5` → severity=4），让断言真正跨过位域提取，
而不是 0 比 0。渲染输出也纳入断言：

```
Version:            00000004    Severity:           00000004 (Error)
```

## 自检：L1e 不等于「断言非重言式」

CI 的 **L1e 破坏性反向验证**（移走 `lib/` 与 `include/`）能证明
**测试真依赖被测包**，但证明不了**断言本身会不会失败**。

补做变异测试：把期望值改坏，确认对应断言确实变红，并在 `notes.md` 记录。
这同时满足 R34 / R51 对「断言真实有效」的举证要求。

## 影响

适用于一切「目标平台缺少底层能力但仍需交付并测试」的包，避免两类 CI 事故：

- **偶发红**：硬编码身份相关返回码。
- **恒绿假绿**：计数型返回值当成状态码 0 比较。

## 关联

`E237`（接口缺失但主体可用）、`E245`（syscall shim 边界）。
