# 消费者测试遇「未初始化链表节点」：SIGSEGV 随 ASLR 漂移的栈外定位与桩层清零分配后端

- **条目 ID**：E999-draft-B183（草稿，待主编审核）
- **来源**：kamailio-presence/6.0.6 适配（18 个 presence 家族模块，OHOS aarch64，零补丁）
- **类别**：测试策略 / stub / 内存 / runtime　**严重度**：warning
- **触发阶段**：testing / runtime

## 现象

消费者测试（dlopen + 契约/行为用例）在**同一二进制、同一用例、连续运行**下随机 SIGSEGV：

```
[FAULT] sig=11 si_addr=0x40000018 pc=0 (unknown)+0x0
RUN_RC=139
```

故障点落在测试桩调用栈内（本包为 `kam_chain_len_steps`），崩溃地址每次运行不同，
极易被误判为「桩层写错」或「用例写错」。

## 根因

被测库存在**未初始化链表节点**：

- kamailio 6.0.6 `src/modules/xcap_client/xcap_functions.c` 的 `xcapNodeSelAddStep`
  在 `:193-207` 分配 `ns_list_t` 新节点后只设置前驱的 `next`，
  **未给新节点的 `ns->next` 赋值**；
  同文件 `:186` 的 `step_t` 分支有 `s->next = NULL`，ns 分支漏写。
- kamailio 的 `pkg_malloc` 后端**不保证清零**（真机默认 `qm_malloc` 亦不保证）。

→ `ns_list` 链尾是堆垃圾 → 任何遍历该链的调用方（用例的链长统计、
模块自身的 `get_node_selector`）读野指针 → SIGSEGV，崩溃地址随 ASLR/堆布局漂移。

## 处理策略（推荐方案）

**桩/测试层内存后端改用清零分配（calloc 语义）**：

```c
static void *kam_stub_xmallocxz(unsigned long size) {
    void *p = calloc(1, size);   /* 上游未初始化的 next 字段因此为 NULL */
    if (p) kamailio_stub_count_xmallocxz++;
    return p;
}
```

链遍历自然终止，被测路径恢复确定可复现（本包 e2e 362 项断言连跑 3 次全绿）。
注意：这是**测试设施层的处置**，不改上游源码（零补丁路线）；上游缺陷同时在
`notes.md` 与本条目登记，供真机集成方评估。

## 回退方案（ptrace 不可用时）

OHOS 设备上 `/data/service/hnp/bin/gdb`、`lldb` 均报
`warning: ptrace: Permission denied`，无法直接追踪。改用：

1. **信号处理器 + dladdr**：在用例内安装 SIGSEGV 处理器，用
   `backtrace()`/`dladdr()` 打印出错符号与偏移，替代 gdb 的栈回溯；
2. **独立最小探针二分**：写只调用被测函数的最小探针（本包 `probe_addstep.c`），
   先证明桩侧分配/返回正常（如 `size=48`、`ns_no=1`、step `"a:entry"`），
   再回到用例层定位；
3. **stderr 无缓冲输出**：崩溃前 stdout 缓冲会丢失，关键轨迹走 stderr 直写。

## 禁止策略

不要据「崩溃点固定」或「桩层一定有 bug」下结论：未初始化字段的崩溃地址随
ASLR/堆布局漂移，据此改桩或删用例只会掩盖上游缺陷，且真机部署后同一路径仍会在
用户侧崩溃。

## 验证

```bash
./test_presence_modules_e2e <modules_dir>   # 清零后端：连跑 3 次确定性全绿（362/362）
# 把后端换回 malloc 后端可复现随机 SIGSEGV → 证明缺陷在被测库而非测试设施
```
