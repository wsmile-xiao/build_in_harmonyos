# 路径 B 知识库扩展申请："修改 + 读取"必须是两次独立调用（假通过 / 恒等断言）

## 申请信息

- **申请类型**：路径 B（知识库扩展，10 分候选）
- **关联任务**：#9338 paxctl 0.9
- **关联 PR**：`!9xxx`（`feat/paxctl-0.9`，配方 PR）
- **知识草稿**：`knowledge/drafts/paxctl-0.9-mutate-then-read-separate-invocations.kv` / `.md`
- **草稿 ID**：`DRAFT-PAXCTL-MUTATE-THEN-READ-SEPARATE-INVOCATIONS`
- **提交方式**：草稿与配方归档**同一原子 PR 分支**（`feat/paxctl-0.9`）提交
- **申请日期**：2026-09-17

## 一、为什么这是"可跨仓库复用的知识"

本仓库 `test_package` 的验证目标是"消费者视角下产物真的能用"。而对同时提供
**查看**与**修改**选项的工具（`paxctl -v/-m`、`ip show/set`、`ethtool`、
`sysctl -a/-w`、`hdparm`、`tc`、`git config --get/--set`……），把两者放进同一次
调用是**最自然的写法，也是本批次实测踩到的假通过陷阱**。

本条目给出一个可 30 秒自检的判别法、一个通用改法模板，以及配套的夹具与可写目录
策略。它在 paxctl 0.9 上完整落地并通过 OHOS aarch64 实测（74/74）。

## 二、实测陷阱：合并调用让 `-v` 命中短路分支

```c
/* ❌ 期望看到改动后的串 */
run_capture("-v -m \"%s\"", fixture, buf);
expect(strstr(buf, "-----m-x----") != NULL, "MPROTECT 已禁用");
```

实测：

```
$ paxctl -v -m ./fixture | grep 'PaX flags'
- PaX flags: -------x---- [./fixture]      ← 改动前！修改根本没应用

$ paxctl -m ./fixture && paxctl -v ./fixture | grep 'PaX flags'
- PaX flags: -----m-x---- [./fixture]      ← 改动后
```

**`-v` 命中"仅查看"短路分支，修改被静默跳过。**

两种结局：

| 结局 | 后果 |
| --- | --- |
| 断言写成"改动后" | 直接 FAIL —— 幸运情况，至少暴露了 |
| 断言改成"改动前的基准串" | 测试**全绿却从未验证过任何一次真实改动** —— 恒等断言 |

第二种更难发现：不报错、不超时、覆盖率数字漂亮，只是把一整类功能判成
"从来没人测过"。

### 一行自检（写用例前必做）

```bash
P=paxctl; F=./fixture
diff <($P -v -m $F | grep 'PaX flags') \
     <($P -m $F && $P -v $F | grep 'PaX flags')
```

有差异即命中本条目。本项目已按此自检结果把"合并写法"**明确定为禁止写法并写进
测试源码注释**，避免后来者"优化"回去。

## 三、通用改法

```c
/* ✅ 1) 应用改动，单独断言退出码 */
snprintf(args, sizeof(args), "%s \"%s\"", mutate_args, fixture);
rc = run_capture(args, buf, sizeof(buf));
expect(rc == 0, "应用改动退出码 (期望 0)", "");

/* ✅ 2) 独立读取，解析并断言目标状态 */
snprintf(args, sizeof(args), "-v \"%s\"", fixture);
rc = run_capture(args, buf, sizeof(buf));
extract_flags(buf, flags, sizeof(flags));
expect(strcmp(flags, want_flags) == 0, "标志串", flags);
```

★ 查看选项**本身也要单独断言退出码**：部分工具在合并调用时会以成功码静默跳过修改。

## 四、配套策略

### ① mutate → verify → restore 三态闭环

```
[PASS] paxctl -m <fixture>: 应用改动退出码 (期望 0)
[PASS] paxctl -m <fixture>: 标志串 (期望 "-----m-x----")
[PASS] -z 从 "-p -e -m -r -s" 复位回基准串
[PASS] -z 从 "-P -E -M -R -S" 复位回基准串
[PASS] -z 从 "-m -r -x" 复位回基准串
```

"复位不变量"——从**任意**前置状态都能回到同一基准串——本身就是高价值属性判据。

### ② 夹具用**被测程序自身的二进制副本**

paxctl 操作 ELF 程序头，任何本包产出的 aarch64 ELF 都是合法输入。用 `bin/paxctl`
自身：不引入外部样本，且顺带证明"产物是结构完好、可被工具正确解析的 ELF"
（多轮改写后仍是合法 ELF）。

### ③ 可写目录不得假定 `/tmp`（OHOS 只读）

`test()` 阶段在 `self.build_folder` 下建 scratch 目录并以 argv 传给测试程序；
测试程序**自己再探测一次可写性**，把"目录不可写"与"被测程序有缺陷"区分开：

```c
if (copy_file(g_bin, probe_tmp) != 0) {
    expect(0, "scratch 目录可写（复制夹具成功）", probe_tmp);
    goto summary;
}
expect(1, "scratch 目录可写（复制夹具成功）", "");
remove(probe_tmp);
```

## 五、顺带标定的确定性行为（已写成判据）

paxctl 0.9 的 12 字符标志串：每 2 字符一个槽，**偶下标 = "已启用"字母，
奇下标 = "已禁用"字母**。

| 下标 | 0/1 | 2/3 | 4/5 | 6/7 | 8/9 | 10/11 |
| --- | --- | --- | --- | --- | --- | --- |
| 字符 | P/p | S/s | M/m | –/x | E/e | R/r |
| 功能 | PAGEEXEC | SEGMEXEC | MPROTECT | RANDEXEC | EMUTRAMP | RANDMMAP |

基准（`-c` + `-z`）恒为 `-------x----`。逐标志实测（每轮复位后单独施加）：

```
-p → -p-----x----     -P → P------x----
-e → -------x-e--     -E → -------xE---
-m → -----m-x----     -M → ----M--x----
-r → -------x---r     -R → -------x--R-
-s → ---s---x----     -S → --S----x----
组合 -p -e -m -r -s → -p-s-m-x-e-r
组合 -P -E -M -R -S → P-S-M--xE-R-
```

由此得到一条**标志串 ↔ 说明行一致性**属性：标志串里每个非 `-` 位都必须有对应的
`"<功能> is enabled|disabled"` 说明行。

## 六、实测结果

```
=== paxctl 0.9 消费者测试 ===
── paxctl -m <fixture>
  [PASS] paxctl -m: 应用改动退出码 (期望 0)
  [PASS] paxctl -m: 标志串 (期望 "-----m-x----")
  [PASS] paxctl -m: 标志串为 12 字符且字符集合法
  [PASS] paxctl -m: 12 位标志串与说明行一致
...
=== 汇总: 74 通过, 0 失败 ===
```

74 条断言：错误路径 13、`-c` 转换 5、10 个单标志 × 4、2 个组合标志 × 4、
复位不变量 3、夹具完好性 2、scratch 可写性 1。

## 七、可套用范围

| 需警惕的工具 | 查看 | 修改 |
| --- | --- | --- |
| paxctl | `-v` | `-m` / `-M` / `-p` … |
| ip | `link show` | `link set` |
| ethtool | `ethtool dev` | `ethtool -s dev` |
| sysctl | `-a` | `-w` |
| hdparm | `-I` | `-d1` |
| tc | `qdisc show` | `qdisc change` |
| git config | `--get` | `--set` |

## 八、请主编审阅

本条草稿是**判据设计规约**，在 paxctl 0.9 上完整落地并通过 OHOS aarch64 实测
（74/74）。落地过程中真实命中过"合并调用导致 `-v` 只回显旧状态"这一假通过陷阱，
已在草稿中作为可自检条目记录。若通过，请按 promote 流程转入正式知识库。
