# "修改 + 读取"必须是两次独立调用

> Draft: `DRAFT-PAXCTL-MUTATE-THEN-READ-SEPARATE-INVOCATIONS`
> Stem: `paxctl-0.9-mutate-then-read-separate-invocations` — 与同 stem 的 `.kv` 成对
> 实例：paxctl 0.9（`archives/p/paxctl/0.9`，PR !9xxx）

## 基本信息

- **ID**: `DRAFT-PAXCTL-MUTATE-THEN-READ-SEPARATE-INVOCATIONS`
- **严重度**: 4（**恒等断言**——测试永远绿，却从未验证过任何一次真实改动）
- **类别**: test-design, false-green, ci-gate
- **触发工具**: ci（L1 测试执行验证）
- **阶段**: testing

## 问题：一次调用里同时"改"和"看"

很多 CLI 同时提供**查看状态**与**修改状态**两类选项：

| 工具 | 查看 | 修改 |
| --- | --- | --- |
| paxctl | `-v` | `-m` / `-M` / `-p` … |
| ip | `link show` | `link set` |
| ethtool | `ethtool dev` | `ethtool -s dev` |
| sysctl | `-a` | `-w` |
| hdparm | `-I` | `-d1` |
| tc | `qdisc show` | `qdisc change` |
| git config | `--get` | `--set` |

写消费者测试时最自然的写法是把它们放在同一次调用里，期望输出直接显示新状态：

```c
/* ❌ 期望看到改动后的串 */
run_capture("-v -m \"%s\"", fixture, buf);
expect(strstr(buf, "-----m-x----") != NULL, "MPROTECT 已禁用");
```

**实测 `paxctl -v -m <file>` 输出的是 `-------x----`（改动前）。**
`-v` 命中了"仅查看"的短路分支，**修改根本没有被应用**。

这有两种结局：

| 结局 | 后果 |
| --- | --- |
| 断言写成"改动后" | 直接 FAIL，**幸运情况**——至少暴露了 |
| 断言改成"改动前的基准串" | 测试**全绿却从未验证过任何一次真实改动**——无论传什么修改选项，`-v` 都只回显旧状态 |

第二种是**恒等断言**：不报错、不超时、覆盖率数字漂亮，只是把一整类功能判成了
"从来没人测过"。它比崩溃更难发现。

### 一行自检

```bash
P=paxctl; F=./fixture
$P -v -m $F | grep 'PaX flags'      # → - PaX flags: -------x---- [./fixture]   ← 改动前！
$P -m $F && $P -v $F | grep 'PaX flags'   # → - PaX flags: -----m-x---- [...]    ← 改动后
```

两条输出不同即命中本条目。

## 方案：拆成两次独立调用，各断言退出码

```c
/* ✅ 1) 应用改动 */
snprintf(args, sizeof(args), "%s \"%s\"", mutate_args, fixture);
rc = run_capture(args, buf, sizeof(buf));
expect(rc == 0, "应用改动退出码 (期望 0)", "");

/* ✅ 2) 独立读取 */
snprintf(args, sizeof(args), "-v \"%s\"", fixture);
rc = run_capture(args, buf, sizeof(buf));
extract_flags(buf, flags, sizeof(flags));
expect(strcmp(flags, want_flags) == 0, "标志串", flags);
```

## 五个要点

### ① 写用例前先做"合并 vs 拆分"对比

```bash
P -v -m F | grep 'PaX flags'                 # 合并
P -m F && P -v F | grep 'PaX flags'          # 拆分
```

两者输出不同 → 把合并写法**明确定为禁止写法并写进注释**，避免后来者"优化"回去。

### ② 查看选项本身也要单独断言退出码

部分工具在"查看+修改"合并时会**以成功码静默跳过修改**——只看输出不看退出码
就会漏掉。

### ③ 建 mutate → verify → restore 三态闭环

```
[PASS] paxctl -m <fixture>: 应用改动退出码 (期望 0)
[PASS] paxctl -m <fixture>: 标志串 (期望 "-----m-x----")
[PASS] -z 从 "-p -e -m -r -s" 复位回基准串
[PASS] -z 从 "-P -E -M -R -S" 复位回基准串
[PASS] -z 从 "-m -r -x" 复位回基准串
```

"复位不变量"（从**任意**前置状态都能回到同一基准串）本身就是高价值的属性判据。

### ④ 夹具用**被测程序自身的二进制副本**

paxctl 操作 ELF 程序头，任何本包产出的 aarch64 ELF 都是合法输入。用 `bin/paxctl`
自身：

- 不引入外部样本；
- 顺带证明"产物是结构完好、可被工具正确解析的 ELF"（多轮改写后仍是合法 ELF）。

### ⑤ 可写目录不得假定 `/tmp`

OHOS 上 `/tmp` 只读。正确做法：`test()` 阶段在 `self.build_folder` 下建 scratch
目录并以 argv 传给测试程序，**测试程序自己再探测一次可写性**（写探针文件并检查
返回值），把"目录不可写"与"被测程序有缺陷"区分开：

```c
if (copy_file(g_bin, probe_tmp) != 0) {
    expect(0, "scratch 目录可写（复制夹具成功）", probe_tmp);
    goto summary;
}
expect(1, "scratch 目录可写（复制夹具成功）", "");
remove(probe_tmp);
```

## 12 字符标志串（paxctl 0.9 实测标定）

每 2 字符一个槽：**偶下标 = "已启用"字母，奇下标 = "已禁用"字母**。

| 下标 | 0/1 | 2/3 | 4/5 | 6/7 | 8/9 | 10/11 |
| --- | --- | --- | --- | --- | --- | --- |
| 字符 | P/p | S/s | M/m | –/x | E/e | R/r |
| 功能 | PAGEEXEC | SEGMEXEC | MPROTECT | RANDEXEC | EMUTRAMP | RANDMMAP |

基准（`-c` 转换 + `-z` 复位后）恒为 `-------x----`。逐标志实测（每次复位后单独施加）：

```
-p → -p-----x----     -P → P------x----
-e → -------x-e--     -E → -------xE---
-m → -----m-x----     -M → ----M--x----
-r → -------x---r     -R → -------x--R-
-s → ---s---x----     -S → --S----x----
组合 -p -e -m -r -s → -p-s-m-x-e-r
组合 -P -E -M -R -S → P-S-M--xE-R-
```

由此还得到一条**标志串 ↔ 说明行一致性**属性：标志串里每个非 `-` 位都必须有对应的
`"<功能> is enabled|disabled"` 说明行（偶下标 enabled、奇下标 disabled）。

## 实测结果

```
=== paxctl 0.9 消费者测试 ===
...
=== 汇总: 74 通过, 0 失败 ===
```

74 条断言：错误路径 13、转换 5、10 个单标志 × 4、2 个组合标志 × 4、
复位不变量 3、夹具完好性 2、scratch 可写性 1。

## 参考实现

- `archives/p/paxctl/0.9/test_package/test_paxctl.c`
- `archives/p/paxctl/0.9/test_package/conanfile.py`（scratch 目录构造与传参）
