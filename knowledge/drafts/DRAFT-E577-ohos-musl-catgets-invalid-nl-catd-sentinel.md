# E577 — OHOS musl catgets() 对无效 nl_catd 哨兵值解引用导致 SIGSEGV

> Contributor: Awstme <awstme@qq.com> | Status: Draft | Updated: 2026-09-15
> Source: lout 3.43.4 OHOS 适配（无补丁时所有排版运行 SIGSEGV；帧回溯定位
> condcatgets 展开的 catgets() 调用点；哨兵检查 4 行后全量用户手册测试全绿）

## 编号说明

跨目录扫描：graph 已占 E573/E574（及 E543–E572 全段），drafts 已占
E575/E576/E579（含 `DRAFT-` 前缀式与 `E<id>-draft-<hash>` 式两种形态），
**最小空号 = E577**。创建后回查无同 ID 并发草稿。

## 错误特征

- 编译**零错误零告警**；
- glibc 开发机/交叉编译产物运行正常；
- OHOS（musl）目标机上**一走到 message catalog / 错误消息路径就崩**：

```text
$ ./lout -s hello.lout -o hello.ps
Segmentation fault (core dumped)        # rc=-11 / signal 11
```

崩溃点**分散**在程序内所有 `catgets()`/其包装宏展开处（对 lout 是
30+ 处错误消息宏），任何一次触发都停在同一族调用上。

## 触发条件

- libc: OHOS musl（目标机）
- 程序启动时调用 `catopen()`，且目标机上 message catalog 文件不存在
  （交叉环境常态——locale 树未安装）
- 代码只对返回值判 NULL，未判 POSIX 哨兵 `(nl_catd)-1`

## 根因分析

POSIX 规定 `catopen()` 失败返回 **`(nl_catd)-1`**（全 1 位模式的哨兵，
**不是 NULL**）：

```c
nl_catd cat = catopen("lout", 0);   // OHOS 上 catalog 不存在 → 返回 (nl_catd)-1
if (cat)                             // ← 只判 NULL，-1 是"真"值，通过了！
    msg = catgets(cat, set, no, s);  // musl: 解引用 0xFFFF...F → SIGSEGV
```

- **glibc 的 `catgets()` 对无效描述符防御性容错**——返回 fallback 字符串，
  程序继续跑，开发者 20 年不知有此问题（lout 正是如此）；
- **musl（OHOS libc）不做该校验**——按描述符直接解引用 → 非映射页 →
  SIGSEGV。

这与 glibc/musl 的设计哲学一致：glibc 大量 API 带防御性 fallback，
musl 严格按 POSIX 契约要求调用方自己保证参数有效（参见
knowledge/musl-glibc-developer-impact.md「容错差异」主题）。

上游 lout 3.43 曾对 `catclose()` 打过同类补丁（先判 `cat != (nl_catd)-1`
再关闭），但漏了 `catgets` 路径——说明哨兵问题在上游已知但未修全。

## 最小修复（lout 3.43.4 实测）

`externs.h` 的包装宏加哨兵检查（4 行）：

```c
/* catopen() returns (nl_catd)-1 on failure; passing it to catgets() is UB
   (glibc tolerates it, OHOS musl does not).  Same guard as the catclose()
   fix in 3.43. */
#define condcatgets(cat, set, msg, s) \
  ((cat) != (nl_catd)0 && (cat) != (nl_catd)-1 ? catgets(cat, set, msg, s) : s)
```

通用修复算法（任何受影响程序）：

1. 定位所有 `catgets()` 调用（含包装宏展开）；
2. 在调用前同时排除 `NULL` 与 `(nl_catd)-1` 两个无效值（宏或内联判断）；
3. 保留 fallback 字符串路径（`s`）——与 glibc 行为对齐；
4. **不要**动 `catopen()` 调用本身，**不要**关闭 locale 功能。

## 诊断流程

1. 症状归一：glibc 正常 + OHOS 一运行就段错误 + 二进制用到 `nl_types.h`
   （`grep -rn "nl_types\|catopen\|catgets" src/`）；
2. 帧指针回溯（无符号表也可：`__builtin_frame_address` 链 + `/proc/self/maps`
   文本基址换算偏移）确认崩溃帧在 `catgets` 族调用点；
3. 检查 `catopen()` 返回值是否被检查（哨兵 vs NULL）；
4. strace：崩溃前有 catalog `openat()` ENOENT 但进程继续运行。

## 安全边界

- 哨兵检查只增加防御性判断，**不改变** glibc 上的行为（glibc 的容错路径
  与 fallback 结果一致）；
- 不引入新的依赖或全局状态；
- 修复必须以最小补丁形式进入源码（可审计、可回溯），禁止在构建期用
  `-DLOCALE_ON=0` 一关了之（功能损失），禁止 strip/忽略信号掩盖崩溃。

## 适用范围

- ✅ C/C++ 程序，任何用 `catopen`/`catgets` 做 message catalog 的代码；
- ✅ 症状面：glibc 正常 / musl SIGSEGV 的运行期段错误；
- ❌ 不适用于：`catopen` 返回值已正确检查哨兵的程序；纯链接错误
  （符号缺失，那是 E169 argp 家族）；`setlocale` 类初始化差异。

## 重复性检索结论

检索范围：knowledge/graph 544 条 + knowledge/drafts 629 份 + 主题文档
（musl-compat.md、musl-glibc-developer-impact.md、musl-glibc-full-comparison-*
两个、error-patterns.md）。

- `grep -rli "catgets\|catopen\|nl_catd\|nl_types" knowledge/graph knowledge/drafts`
  → **零命中**；
- musl 系列文档覆盖 setlocale/locale 名字长度/线程等主题，无 message
  catalog 哨兵条目；
- 最相近条目：
  - **E169 (argp-musl-gap-bridge)**：同属 glibc/musl 差异，但那是
    **符号缺失**（链接期），本条是**运行期语义差异**（容错 vs 不容错）；
  - **E520 (raw-makefile-strip-musl-symbols)**：同涉 musl 符号，但主题是
    strip 污染 + 构建系统，与本条无重叠修复点；
  - **E077/E079 (OHOS SDK 签名/文件系统)**：同为 OHOS 特有运行环境差异，
    领域（签名/hmdfs vs libc 语义）不同。
- 结论：**新根因，无现有条目覆盖**，具备跨库复用价值（任何带 message
  catalog 的工具移植到 OHOS 都会踩到），建草稿 E577。
