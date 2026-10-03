# DRAFT-sockstat-0.4.2-abort-signal-triage-139-vs-134

**错误模式**：崩溃取证断言用「退出码区间」概括崩溃（如 `rc >= 128 && rc <= 139`），
在受限平台上会把**平台权限崩溃冒充成上游缺陷证据**。CI 不会变红，结论却悄悄失真。

- 来源：sockstat 0.4.2 适配 W4 独立审计 P1（2026-10-02）
- 严重度：🟡 medium（不阻塞构建，但会让验证结论不可信）

## 根因

为上游缺陷写「崩溃取证」断言时，常见写法是按退出码区间概括：

```bash
elif [ "${TOOL_RC}" -ge 128 ] && [ "${TOOL_RC}" -le 139 ]; then
    defect "-G 上游 NULL dereference"
```

开发机上成立，换到受限平台就失真。sockstat 0.4.2 的 `-G root` 有**两条崩溃路径，
根因完全不同**：

| rc | 信号 | 源码位置 | 根因 |
|---|---|---|---|
| 139 | SIGSEGV | `sockstat.c:731` | `getpwnam(*((grp->gr_mem)++))` 把 NULL 终止项解引用 —— 真·上游缺陷 |
| 134 | SIGABRT | `sockstat.c:590-591` | `handle_missing_file()` 因 `/proc/net` EACCES 触发 `abort()` |

134 那条**比 731 早约 140 行，根本走不到缺陷代码**。

- 开发机 `/proc/net` 可读 → 只看到 139 → 区间断言通过
- OHOS 真机 `/proc/net` 被沙箱拒 → 只看到 134 → 区间断言**照样通过**，但结论已是假的

同一轮审计还发现一个同源问题：T6 的**三个分支全调 `defect()`**，而 `DEFECT`
计数不影响退出码 —— 该取证断言永远不可能失败。

## 推荐做法

崩溃取证断言必须按**信号**分流，不能按区间：

1. **先排序崩溃路径**：`grep -n "abort()\|SIGSEGV\|handle_missing_file" <src>/*.c`，
   算出各自行号，确认「哪条路径在受限平台上会先触发」。
2. **断言分流顺序**：先判受限特征串（`can not open file /proc/net/`）命中 → 归
   `RESTRICTED` 并说明「本环境无法证明该缺陷」；再判具体信号
   （139 = 上游缺陷 / 134 = 上游主动 abort）。
3. **兜底分支一律 `fail`**，绝不放行到 `defect` 计数 —— 否则取证断言永不可能失败。
4. 缺陷若在受限平台确实不可达，就把源码级论证写进 `notes.md`，让测试如实记
   `RESTRICTED`，**不要伪造一条跑不出来的证据**。

## 修正后的形态

```bash
run_sockstat -G root
if [ "${TOOL_RC}" -eq 199 ]; then
    skip "..."
elif echo "${TOOL_OUT}" | grep -q "can not open file /proc/net/"; then
    restrict "...沙箱前置拦截（abort 发生在读表阶段，早于 gr_mem 解引用）..."
elif [ "${TOOL_RC}" -eq 139 ]; then
    defect "...确认上游 NULL dereference（rc=139 SIGSEGV）..."
elif [ "${TOOL_RC}" -eq 0 ]; then
    defect "...本次未复现，上游可能已修复..."
else
    fail "...既非 SIGSEGV 也非沙箱 abort，行为不可解释..."
fi
```

实测：开发机 `rc=139` → `defect`；受限分支 `rc=134` → `RESTRICTED`（修正前会
被误记为 defect 证据）。

## 适用范围

- 为上游已知崩溃 / NULL deref 写取证断言的 `test_package`
- 同一程序存在多条 abort 路径（读表失败 + 逻辑缺陷）的诊断类工具
- 需要在真机与开发机之间复用同一套测试脚本的适配任务
