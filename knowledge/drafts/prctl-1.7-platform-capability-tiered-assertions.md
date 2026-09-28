# 不要把本地验证环境的能力固化成断言

> Draft: `DRAFT-PRCTL-PLATFORM-CAPABILITY-TIERED-ASSERTIONS`
> Stem: `prctl-1.7-platform-capability-tiered-assertions` — 与同 stem 的 `.kv` 成对
> 实例：prctl 1.7（`archives/p/prctl/1.7`，PR !10694）——**CI 实测踩中并修正**

## 基本信息

- **ID**: `DRAFT-PRCTL-PLATFORM-CAPABILITY-TIERED-ASSERTIONS`
- **严重度**: 4（**成片假失败**——10 条断言因判据假设了本地环境而集体失败）
- **类别**: test-design, portability, false-fail, ci-gate
- **触发工具**: ci（L1 测试执行验证）
- **阶段**: testing

## 一、真实发生的故障

`archives/p/prctl/1.7` 首次提交后 CI 失败（build #50032），失败集中在 5 个平台专有
选项 × 2 条断言 = **10 条**：

```
── prctl --unaligned=silent
  [FAIL] 退出码 (期望 1) — 实际 0
  [FAIL] 内容: 输出含 "does not implement set_unaligned prctl feature" — 实际输出: Starting a shell
── prctl --fpemu=signal
  [FAIL] 退出码 (期望 1) — 实际 0
  [FAIL] 内容: 输出含 "does not implement set_fpemu prctl feature" — 实际输出: Starting a shell
=== 汇总: 61 通过, 10 失败 ===
```

**错误信息本身就是答案**：`实际输出: Starting a shell` 说明被测程序**工作完全正常**
——选项被接受了，于是走到了"没有给命令就起一个 shell"的默认动作。

## 二、根因：本地内核 ≠ CI 真机内核

同一个二进制、同一次编译、同一组参数：

| 环境 | `prctl(PR_SET_UNALIGN, PR_UNALIGN_NOPRINT)` | 工具行为 | 退出码 |
| --- | --- | --- | --- |
| 本地 WSL Ubuntu aarch64（qemu 执行） | 返回 **EINVAL** | 打印 `This platform does not implement set_unaligned prctl feature.` | **1** |
| OpenHarmony CI worker | 返回 **0**（成功） | 继续执行，`-v` 回显 `Set "unaligned" to "silent"` | **0** |

写判据时我把**本地观测到的行为**当成了"平台事实"：

```c
/* ❌ 单分支硬断言：把本地内核的行为写死 */
case_expect("--unaligned=silent", 1, u_silent, 1, 0);
```

而 `--unaligned` / `--fpemu` 虽然在文档里标注为 ia64 专有，**内核是否真的返回
EINVAL 是运行期事实，不是编译期事实**。

> ★ 关键区分：
> - **编译期缺失**（`#ifdef` 挡住、符号不存在）→ 确定的，可以写死断言；
> - **运行期拒绝**（syscall 返回 EINVAL / ENOSYS）→ 不确定的，**必须运行时分级**。

## 三、修法：双分支运行时分级，两端都断言

```c
static void case_platform_option(const char *feat, const char *val)
{
    snprintf(args, sizeof args, "--%s=%s -v", feat, val);
    snprintf(notimpl, sizeof notimpl, "does not implement set_%s prctl feature", feat);
    snprintf(conf,    sizeof conf,    "Set \"%s\" to \"%s\"", feat, val);

    rc = run_capture(args, buf, sizeof buf);
    if (rc != 0) {
        /* 分支 A：平台不实现 → 必须明确报错，不许静默成功 */
        expect(strstr(buf, notimpl) != NULL, "打印平台不实现错误", buf);
        printf("  [INFO] 平台不实现 --%s（退出码 %d）\n", feat, rc);
    } else {
        /* 分支 B：平台实现 → 必须回显设置结果，且不得同时报不实现 */
        expect(strstr(buf, conf)    != NULL, "回显设置结果", buf);
        expect(strstr(buf, notimpl) == NULL, "成功时不报平台不实现", "");
        printf("  [INFO] 平台实现 --%s\n", feat);
    }
}
```

三个要点：

### ① 两个分支都要有断言

只断言一端等于把判据退化成"环境适配"；**两端都断言**，无论跑在哪个内核上
都真正验证了同一条契约：

> **合法取值必须得到明确结果，不得静默通过。**

### ② 打印实际走了哪个分支

```
  [INFO] 平台不实现 --unaligned（退出码 1）      ← 本地
  [INFO] 平台实现 --unaligned                   ← OHOS
```

不打印的话，日志里看不出环境差异，下次踩同一个坑。

### ③ 与平台无关的错误路径单独抽成稳定基线，保持硬断言

```c
case_expect("--unaligned=bogus", 1, NULL, 0, /* want_usage */ 1);
```

非法取值必须在**所有**平台回落用法并退出非 0 —— 这条在本地与 OHOS 上**都通过**，
是真正可依赖的契约（不能因为平台专有选项要分级，就把整个选项族都放软）。

## 四、实测结果（两个环境都全绿）

```
本地 WSL Ubuntu aarch64：
  [INFO] 平台不实现 --unaligned（退出码 1）
  [INFO] 平台不实现 --fpemu（退出码 1）
  === 汇总: 66 通过, 0 失败 ===

OpenHarmony CI worker（预期）：
  [INFO] 平台实现 --unaligned
  [INFO] 平台实现 --fpemu
  === 汇总: 66 通过, 0 失败 ===
```

同一份判据、同一个二进制，两个内核都能验证契约。

## 五、可套用范围

| 工具/选项 | 依赖的平台能力 | 是否必须分级 |
| --- | --- | --- |
| `prctl --unaligned` / `--fpemu` | `PR_SET_UNALIGN` / `PR_SET_FPEMU` | **是**（本例） |
| `prctl --mcekill` | `PR_MCE_KILL` | **是**（先 `-q` 探测） |
| `ifmetric` | netlink 路由接口 | 是 |
| `zcfan` | sysfs hwmon | 是（路径是否存在） |
| `hdparm` 多数操作 | ATA 直通 | 是 |
| `perf` 事件 | 具体 PMU | 是 |
| `ethtool -K` | 驱动特性位 | 是 |
| `sysctl` 架构相关 knobs | 内核配置 | 是 |
| `mount` fs 专有选项 | 内核 fs 支持 | 是 |
| `#ifdef` 挡住的选项 | 编译期缺失 | **否**（可写死） |

## 六、判别手法（三步，30 秒）

1. **同一二进制两处各跑一次**，对比退出码：
   ```bash
   "<bin>" --unaligned=silent -v; echo $?      # 本地
   # CI worker 上同一条命令
   ```
2. 退出码不同 → **该行为依赖环境**，判据必须分级。
3. 报错信息里出现"程序正常继续执行"的迹象（本例 `Starting a shell`）→
   **优先怀疑判据，而不是被测程序**。

## 七、与本批次其它判据的关系

本条是判据工具箱的第 7 条，来源从"设计规约"升级为**真实 CI 故障复盘**：

| 判据 | 适用 | 参考 |
| --- | --- | --- |
| 往返一致性 | 可逆转换 | `DRAFT-LUNAR-ROUNDTRIP-PROPERTY-CONSUMER-TEST` |
| 结构不变量 | 不可逆但输出有约束 | `DRAFT-LETTERIZE-STRUCTURAL-INVARIANT-CONSUMER-TEST` |
| 两段式调用 | 有状态的修改类工具 | `DRAFT-PAXCTL-MUTATE-THEN-READ-SEPARATE-INVOCATIONS` |
| 干跑 + 独立历法 | 输出与当前时刻相关 | `DRAFT-SNOOZE-TIMELESS-DRYRUN-CALENDAR-CROSSCHECK` |
| 合成夹具 + 往返属性 | 解析结构化二进制输入 | `DRAFT-UNYAFFS-SYNTHESIZED-FIXTURE-ROUNDTRIP` |
| **本地环境能力不得固化**（本条） | 行为依赖内核/平台能力 | — |

## 八、参考实现

- `archives/p/prctl/1.7/test_package/test_prctl.c` — 66 条断言
  （`case_platform_option()` 双分支分级 + `-q` 能力探测 + 稳定基线）
