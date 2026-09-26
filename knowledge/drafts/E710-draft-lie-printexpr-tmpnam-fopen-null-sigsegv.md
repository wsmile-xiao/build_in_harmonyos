# E710（草稿）— 上游 printexpr 对 tmpnam+fopen 不判 NULL：OHOS /tmp 只读下 SIGSEGV(rc=139)

- 软件：lie 2.2.2（LiE 李群计算机代数系统）
- 触发任务：任务卡 8460（积分赛，分支 `feat/lie-2.2.2`）
- 日期：2026-09-24
- 状态：DRAFT — 待主编审核提升为 E 条目

## 现象

上游三入口测试全绿（`progs/test` 23/23、`progs/testsuite` 18/18、`progs/maxsub0` 载入正常，
TOTAL=41 全过），但消费者一执行 `?help` / `?dim` 查询即进程崩溃，rc=139（SIGSEGV），输出 0 字节。

## 根因

`print.c:601`（`printexpr()`）：

```c
{ tmpnam(tmpfile); cur_out=fopen(tmpfile, "w"); invoke_pager=true; }
```

两个返回值都不判：OHOS 设备 `/tmp` 只读（EROFS），`tmpnam` 产名正常但 `fopen` 恒返 **NULL**；
下一段 `printdocument` 经 `cur_out`（FILE*）写入即解引用 NULL → SIGSEGV。

关键判读：

1. **同文件有先例**：`learn.c:135` 与 `print.c` 其余三处分页点都有
   `cur_out==stdout→stdout` 回退，唯此处缺失——属上游 portability 漏判，不是平台差异
   （因此**不需要** `__OHOS__` 宏，PF5 免拦，走 portability 补丁）。
2. **上游测试 0 命中**：三个测试入口都不含 `?` 查询，缺陷不在上游断言面上——
   「测试全绿 ≠ 消费者不崩」的典型形态，只看测试面会漏判。
3. **探针双支定性**：同一 rc=139 有两个独立成因——①自家探针 `.c` 缺
   `#include <stdlib.h>`，`getenv` 隐式声明（int 返回被截断成指针）自身即崩；
   ②上游 printexpr 真缺陷。**必须先修探针三连复跑 rc=0** 排除①，再对上游定性②，
   否则会把探针缺陷记到上游账上（或反之把真缺陷当成探针噪声吞掉）。

## 修法（portability 补丁）

`archives/l/lie/2.2.2/patches/0001-printexpr-null-check.patch`（strip 1）：

```c
{ tmpnam(tmpfile); cur_out=fopen(tmpfile, "w");
  if (cur_out==NULL) { cur_out=stdout; invoke_pager=false; }
  else invoke_pager=true; }
```

- 失败回退 stdout、不起分页器——与同文件既有形态对齐；
- 无平台宏，PF5 免拦；
- 双证：修前 rc=139（`w0/pre.out` 0B）→ 修后 rc=0（`w0/post2.out` 364B 帮助正文）；
- 三关：NUL=0、`@@`=1、真 apply 后与 `w0/ptree/LiE/print.c.patched` 逐字节 cmp rc=0；
- 消费者回归：`test_package/test.sh` 断言 `?help` rc=0 且输出含 INFO 帮助数据（7 条断言之一）。

## 复现 / 验证命令（设备可直接执行，均落 $TASK_DIR 不用 /tmp）

```bash
# 补丁树（修后 rc=0 且有输出）
printf '?help\n' | /storage/Users/currentUser/tmp/lie-2.2.2/w0/x/LiE/lie 2>&1 | head -5; echo rc=$?

# 补丁三关之 apply 关（dry-run 即可证明可 apply）
cd /storage/Users/currentUser/tmp/lie-2.2.2/applychk
patch -p1 --dry-run < /storage/Users/currentUser/ws/worktrees/lie-2.2.2/archives/l/lie/2.2.2/patches/0001-printexpr-null-check.patch && echo PATCH_OK
```

## 可复用面

任何在只读 `/tmp`（EROFS）环境用 `tmpnam`/`tmpfile` + `fopen` 且不判返回值的旧 C 程序，
其交互查询/输出分页路径都同型；判据三条可直接套用：①同文件有无既有回退先例
（决定 portability 补丁 vs 止损）；②上游测试是否命中该路径（决定「测试全绿」可信度）；
③探针自身先修后定（rc=139 双支定性顺序）。
