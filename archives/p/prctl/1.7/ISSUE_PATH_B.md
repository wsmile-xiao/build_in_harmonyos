# 路径 B 知识库扩展申请：不要把本地验证环境的能力固化成断言（平台专有行为必须运行时分级）

## 申请信息

- **申请类型**：路径 B（知识库扩展，10 分候选）
- **关联任务**：#9703 prctl 1.7
- **关联 PR**：`!10694`（`feat/prctl-1.7`，配方 PR）
- **知识草稿**：`knowledge/drafts/prctl-1.7-platform-capability-tiered-assertions.kv` / `.md`
- **草稿 ID**：`DRAFT-PRCTL-PLATFORM-CAPABILITY-TIERED-ASSERTIONS`
- **提交方式**：草稿与配方归档**同一原子 PR 分支**（`feat/prctl-1.7`）提交
- **申请日期**：2026-09-18

## 一、这条知识来自本 PR 的一次**真实 CI 失败复盘**

本仓库的移植流程会在提交前用「本地交叉编译 + qemu 执行」做功能预验证。这很有用，
但**本地执行用的仍是宿主内核**（Ubuntu aarch64），不是 CI 目标机（OpenHarmony）。
本 PR 首次提交后 CI 失败（build #50032），失败集中在 5 个平台专有选项 × 2 条断言
= **10 条**：

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
—— `--unaligned=silent` 被接受了，于是走到了"没有给命令就起一个 shell"的默认动作。

## 二、根因：本地内核 ≠ CI 真机内核

同一个二进制、同一次编译、同一组参数：

| 环境 | `prctl(PR_SET_UNALIGN, …)` | 工具行为 | 退出码 |
| --- | --- | --- | --- |
| 本地 WSL Ubuntu aarch64（qemu 执行） | 返回 **EINVAL** | 打印 `This platform does not implement set_unaligned prctl feature.` | **1** |
| OpenHarmony CI worker | 返回 **0**（成功） | 继续执行，`-v` 回显 `Set "unaligned" to "silent"` | **0** |

写判据时把**本地观测到的行为**当成了"平台事实"：

```c
/* ❌ 单分支硬断言：把本地内核的行为写死 */
case_expect("--unaligned=silent", 1, u_silent, 1, 0);
```

`--unaligned` / `--fpemu` 虽在文档里标注为 ia64 专有，但**内核是否真的返回 EINVAL
是运行期事实，不是编译期事实**。

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

1. **两个分支都要有断言**——只断言一端等于把判据退化成"环境适配"；两端都断言，
   无论跑在哪个内核上都验证同一条契约：**合法取值必须得到明确结果，不得静默通过**。
2. **打印实际走了哪个分支**（`[INFO] 平台实现 …` / `[INFO] 平台不实现 …（退出码 1）`）
   —— 否则日志里看不出环境差异，下次踩同一个坑。
3. **与平台无关的错误路径单独抽成稳定基线并保持硬断言**：非法取值
   （`--unaligned=bogus`）必须在所有平台回落用法并退出非 0 —— 这条在本地与 OHOS 上
   **都通过**，不能因为平台专有选项要分级就把整个选项族都放软。

## 四、实测结果（两个环境都全绿）

```
本地 WSL Ubuntu aarch64：
  [INFO] 平台不实现 --unaligned（退出码 1）
  [INFO] 平台不实现 --fpemu（退出码 1）
  === 汇总: 66 通过, 0 失败 ===

OpenHarmony CI worker：
  [INFO] 平台实现 --unaligned
  [INFO] 平台实现 --fpemu
  === 汇总: 66 通过, 0 失败 ===
```

同一份判据、同一个二进制，两个内核都能验证契约。

## 五、判别手法（三步，30 秒）

1. 同一二进制在两处各跑一次，对比退出码：
   ```bash
   "<bin>" --unaligned=silent -v; echo $?
   ```
2. 退出码不同 → **该行为依赖环境**，判据必须分级。
3. 报错信息里出现"程序正常继续执行"的迹象（本例 `Starting a shell`）→
   **优先怀疑判据，而不是被测程序**。

## 六、可套用范围

| 工具/选项 | 依赖的平台能力 | 是否必须分级 |
| --- | --- | --- |
| `prctl --unaligned` / `--fpemu` | `PR_SET_UNALIGN` / `PR_SET_FPEMU` | **是**（本例） |
| `prctl --mcekill` | `PR_MCE_KILL` | **是**（先 `-q` 探测） |
| `ifmetric` | netlink 路由接口 | 是 |
| `zcfan` | sysfs hwmon | 是 |
| `hdparm` 多数操作 | ATA 直通 | 是 |
| `perf` 事件 | 具体 PMU | 是 |
| `ethtool -K` | 驱动特性位 | 是 |
| `sysctl` 架构相关 knobs | 内核配置 | 是 |
| `mount` fs 专有选项 | 内核 fs 支持 | 是 |
| `#ifdef` 挡住的选项 | 编译期缺失 | **否**（可写死） |

## 七、本包其余判据（平台无关的稳定基线）

| 分组 | 内容 |
| --- | --- |
| 版本/用法 | `--version` → `prctl version 1.7` rc0；`-h`/`--help` rc0；无参数/仅 `-v` rc1 + 用法块 |
| 用法块完整性 | 必须列出 `--unaligned=` / `--fpemu=` / `--mcekill=` / `<-q\|<options>>` |
| 非法取值 | `--unaligned=bogus` / `--fpemu=bogus` / `--mcekill=bogus` → rc1 + 用法块（**本地与 CI 都通过**）|
| 非法选项 | `--nope` / `-Z` / `--mcekill`（缺 `=`）→ rc1 + `invalid option` |
| `-q` 查询 | rc0 + 表头 + 平台能力探测（mcekill 是否列出）|
| mcekill set | 平台列出时才断言 `Set "mcekill" to "early\|late\|default"` 且不出现 `Failed to`；未列出打印 `[SKIP]` 并说明原因 |

**66 条断言，本地与 CI 均 0 失败。**

## 八、请主编审阅

本条草稿是**真实 CI 故障的复盘产物**（而非纯设计规约），已在 prctl 1.7 上完整落地，
并在本地与 OpenHarmony 两个内核上都验证通过。若通过，请按 promote 流程转入正式知识库。
