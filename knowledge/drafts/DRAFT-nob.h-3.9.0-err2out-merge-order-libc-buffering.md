# DRAFT-nob.h-3.9.0-err2out-merge-order-libc-buffering：头文件库自带 runner 的 err2out 合并流顺序差异归因

> Contributor: pc7-47 | Status: Draft | Updated: 2026-09-29
> Source: nob.h 3.9.0 适配（feat/nob.h-3.9.0，tsoding/nob.h）
> 对应：`knowledge/drafts/DRAFT-nob.h-3.9.0-err2out-merge-order-libc-buffering.kv`

## 问题现象

nob.h 是"头文件库 + 自带测试驱动"形态（`clang -x c -o nob nob.c && ./nob`，
驱动逐个编译 tests/*.c、运行并把 stdout 与 `tests/<name>.stdout.txt` 快照全文比对）。
OHOS(aarch64) 上 19 个用例 18 个逐字节 PASS，唯独 **chain** 用例：

```text
🚨 [ERROR] UNEXPECTED OUTPUT!
[ERROR] EXPECTED: Uryyb gb fgqree.  (Hello to stdout) 在前
[ERROR] ACTUAL:   Uryyb gb fgqbhg.  (Hello to stderr) 在前
```

EXPECTED 与 ACTUAL 的**内容完全一致**（rot13/hex 结果逐字节相同），仅合并流中
stderr 行与 stdout 行的**到达顺序**相反。单独复跑 3 次均 ORDER_DIFF（确定性复现）。

## 根因分析

chain 用例通过 `err2out=true` 把 hello 程序（先写 stdout、后写 stderr）的
stdout 与 stderr 合并进同一管道再经 rot13→hex 链。本设备 libc（musl 系）下
**stderr 无缓冲（立即写入）、stdout 对管道全缓冲（退出时才 flush）**，于是
合并流中 stderr 内容先于 stdout 内容到达；而上游快照录制于 glibc 环境，两种
libc 产生两个不同的合并顺序——全文 diff 必挂其一。这是 libc stdio 缓冲策略
差异（与 DRAFT-E658 scrub 同族），**不是 nob.h 库功能缺陷**：chain/err2out/
管道数据全部正确，仅顺序敏感。

## 处置与判据（可跨库复用）

1. 对"头文件库/无二进制库 + 自带 runner 驱动 + err2out(或 2>&1) 管道合并 +
   快照全文比对"的测试套：失败用例先 `diff` 确认**行集合完全一致、仅顺序移动**
   （diff 只出现 a/d 移动块，无内容差异行）。
2. 命中即归因 libc 缓冲策略（glibc 全缓冲 vs musl 系行/无缓冲交错），
   不做库门禁失败、不伪造通过、不修改上游测试。如实计入上游用例分母
   （通过数/全量发现数），并在台账注明恢复条件。
3. 与 E658 的差异：E658 给可注入 setvbuf 的应用侧修复；本轮被测物是头文件
   库（无编译产物、无 setvbuf 注入点），处置路径为"判据归因 + 如实计数"，
   属于边界扩展：E658 的"诊断行交错"→ 本轮"合并流整体到达顺序"。

## 验证

- chain 单独复跑 3× ORDER_DIFF（确定性）；其余 18 用例 PASS（`./nob test` RC=1，
  日志 `$HOME/tmp/nob-run-all.log`）。
- 全量通过率 18/19 = 94.7%；当前配置可执行集合 18/19 = 94.7%（全部实例化并执行）。
- merge 行为小实验确认：hello 合并流顺序与本判据一致。