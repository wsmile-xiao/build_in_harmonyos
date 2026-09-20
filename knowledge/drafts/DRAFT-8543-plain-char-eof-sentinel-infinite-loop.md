# DRAFT — plain char 承接 getc() 的 EOF：目标平台上状态机无出口死循环

> Status: DRAFT (contributor 8543) | Source: looktxt/1.4.1 adaptation, task #8543
> Environment: HarmonyOS PC aarch64, OHOS SDK clang 15.0.4（plain char 默认无符号）

## 1. 症状

上游自带的自测（`make test` → `looktxt --test examples/Al.lau`）在真机上**永不返回**，
设备上一个 CPU 被占满，没有任何错误输出：

```
$ timeout 25 ./looktxt --verbose --test examples/Al.lau < /dev/null ; echo rc=$?
rc=124          # 被 timeout 杀掉，不是断言失败
```

这类失败最容易被误记为“设备慢/测试预算不够”。判据是：**超时而非失败**、CPU 满载、
且输入换一个含数字区域的普通文本文件同样挂起。

## 2. 根因

```c
/* looktxt 1.4.1, looktxt.c —— file_scan()（L2336–L2700）扫描主循环 */
    char c;                                   /* L2382 接收变量 */
    do {
      c = lk_tolower(getc(file.SourceHandle)); /* L2419 getc 返回 int；EOF(-1) 落到 char */
      if (c == EOF) { ... }                    /* L2422 无符号 char 下 c==255，永不为 -1 */
      ...                                      /* 循环内还会 fseek 回到文件内位置，pos 恒停在 EOF 处 */
    } while (c != EOF);                        /* L2692 唯一的出口条件 */
```

C 把 plain char 的符号性留给实现决定；本机工具链实测（`clang -dumpmachine` =
`aarch64-unknown-linux-ohos`，`limits.h` 的 `CHAR_MIN == 0`，预定义
`__CHAR_UNSIGNED__`）为无符号。EOF 是 int 域的哨兵值，不是 8 位数据，放进 char 后
不可表示。当 EOF 判定是扫描循环唯一的出口条件时，控制流直接丢失。上游在 x86-64
Linux（plain char 有符号）开发测试，因此该缺陷自发布起长期隐形——Debian 侧正是以
`fix_infinite_loop.patch` 修掉同一行。

插桩实测（同一设备、同一 clang）：未打补丁构建在 `getc()` 返回 -1 时观察到 `char c`
的值为 **255**、`ftell()` 恒为 68137（Al.lau 的文件大小），空转 1.93e6 次仍不退出；
打补丁（`int c`）构建在 EOF 处得到 **-1**，恰好读 68138 次（= 文件大小 + 1）后退出。

与 E419 同源但不同症：E419 是 plain char 被当作**有符号 8 位样本**，数值差 256、
数据仍在；本案是 **哨兵值不可表示**，表现为控制流与可用性故障，且 `-fsigned-char`
只是把目标平台拉回上游假设（实测：未打补丁 + `-fsigned-char` 也不挂起），代码本身
仍是错的，换编译器/换目标又复发。

## 3. 修复（单行类型修正，无平台宏）

```diff
-    char c;
+    int c;
```

`int` 是 `getc()` 的标准返回值域，EOF 因此可表示；hunk 上下文逐字节保留，算法与
测试断言一律未动，可直接向上游提交（P005）。

## 4. 验证（三组同机对照，非“跑一遍看绿”）

输入 `examples/Al.lau`（68137 字节），`stdin=/dev/null`，编译命令
`<ohos-clang> -O2 [-fsigned-char] -o looktxt -g looktxt.c`：

| 场景 | A：上游源码 + 默认选项 | B：上游源码 + `-fsigned-char` | C：打补丁（`int c`）+ 默认选项 |
|---|---|---|---|
| `timeout 25 ./looktxt --verbose --test examples/Al.lau` | rc=124（永久挂起，100% CPU） | rc=0 | rc=0 |
| `make test`（上游自测，5 个官方示例文件） | 不返回 | — | `Test OK`，退出码 0，6/6 用例 |
| `2x3` 矩阵导出（不加 `--fast`） | 挂起 | `1 1 2 / 3 4 5` | `1 1 2 / 3 4 5`（B==C，与本补丁无关的上游缺陷） |
| `2x3` 矩阵导出（`--fast`） | 挂起 | `1 2 3 / 4 5 6` | `1 2 3 / 4 5 6` 逐字正确 |

B 组证明病因是 char 符号性而非文件内容；A/C 组证明补丁是必要条件。不加 `--fast` 的
数值错位（`1 1 2`）是**另一个**上游既有缺陷（`data_get_double()` 的 `fread+sscanf`
分支），与本补丁无关，两组构建行为一致，故未越界修改。

消费者侧 15 条断言全部在打补丁后的安装包上重跑通过，其中第 15 条正是当年挂起
的那条干跑模式调用。

## 5. 通用检查清单

1. `grep -nE 'char +[a-zA-Z_]+ *;'` 与 `grep -n '(g|f)?getc *\('`：同一变量既是 char
   又接收 getc 返回值 → 高度可疑；
2. 该变量是否参与 `== EOF` / `!= EOF` / `== -1` 比较；
3. 目标平台 plain char 符号性：对含 `#include <limits.h>` 的探针文件跑
   `clang -dM -E probe.c | grep -i CHAR_UNSIGNED`（本机命中 `__CHAR_UNSIGNED__`），
   或直接编译运行 `printf("CHAR_MIN=%d", CHAR_MIN)`（本机实测 0）；
   `clang -dumpmachine` 记下目标三元组（本机 `aarch64-unknown-linux-ohos`）；
4. 修复优先落在类型（`int`）而不是编译开关；若代码本意就是有符号 8 位样本，
   才走 E419 的 `-fsigned-char` 路线；
5. 报告时必须给出“未打补丁 → 超时 rc=124”的对照证据，否则无法区分“变慢”与“无出口”；
   对照组建议同时包含「未打补丁 + `-fsigned-char`」，它能把“char 符号性”与其他嫌疑（文件内容、
   算法分支）干净地分开；跑对照时务必 `< /dev/null`，避免把等待标准输入误判成死循环；
6. 写「某函数导致某症状」之前，先用符号级证据定位（`grep -n` 出问题的读取语句 + 打印函数边界），
   把行号写进笔记。凭函数名直觉归因会在独立审计（W4）里被判“文档与源码矛盾”（本案即如此：
   真实位置 `file_scan()` 一度被写成只负责 fast/slow 数值分支的 `data_get_double()`）。
