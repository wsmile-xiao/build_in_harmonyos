# PKG_CHECK_MODULES 让 autoconf 2.72 把 ac_fn_c_try_link 定义排到首次调用之后 ⇒ 链接探测静默假失败，但 configure 退出码仍是 0

> 本条目由 itools 1.1（平台任务 7546 / PR #12629 / HarmonyOS PC aarch64）2026-09-29 的方案 A 落地轮实证产出。
> **它取代旧稿 `DRAFT-itools-1.1-autotools-mixed-toolchain-pairing`**（旧稿把成因归给"conan automake/1.18 与本机 autoconf 混配"），
> 取代理由是旧归因已被单变量最小复现证伪，见 §4。

## 1. 症状与稳定错误签名

configure **正常退出、构建最终成功**，但日志里夹着这类行：

```
checking for pow in -lm... .../configure: line 5065: ac_fn_c_try_link: command not found
checking for error_at_line... .../configure: line 5283: ac_fn_c_try_link: command not found
checking for alarm... .../configure: line 1724: ac_fn_c_try_link: command not found
checking for strcasecmp... .../configure: line 1724: ac_fn_c_try_link: command not found
```

稳定签名 = `configure: line N: ac_fn_c_try_link: command not found`，且 **configure 退出码为 0**（不是崩溃）。
它极易被当成噪音：构建全绿、`conan create` rc=0、消费者测试全过，只有 `config.h` 悄悄变了形：

```
/* #undef HAVE_ALARM */
/* #undef HAVE_STRCASECMP */
```

## 2. 根因

`configure.ac` 里出现 pkg.m4 的 `PKG_CHECK_MODULES` 时，autoconf 2.72 会把 C 链接探测辅助函数
`ac_fn_c_try_link` 的函数体**发在两处，且两处都排在它的首次调用之后**（实测 P 组：首调用 1537 行、首个定义 4594 行、定义块 2 个）。
首次调用位于 `AC_PROG_CC` 之后那批探测里，此时函数尚未定义 ⇒ 每条先被调到的**链接**探测一律 command not found ⇒ 判为"没有"。

由 `try_compile` / `try_run` 完成的探测不受影响——它们的定义（实测 1503 / 1638 行）仍在正常位置，所以
`checking whether the C compiler works... yes`、`checking whether we are cross compiling... no`、
`checking for GNU libc compatible malloc... yes` 都是对的。**这正是本条危险的地方**：关键探测看着全对，只有链接族静默失真。

## 3. 判别方法（30 秒，无需重跑构建）

```sh
u=$(grep -n 'if ac_fn_c_try_link' configure | head -1 | cut -d: -f1)   # 首次调用
d=$(grep -n '^ac_fn_c_try_link ()' configure | head -1 | cut -d: -f1) # 首个定义
k=$(grep -c '^ac_fn_c_try_link ()' configure)                          # 定义块数
# d 非空 且 d > u  ⇒ 命中本条（k 通常同时 > 1）
grep -c 'command not found' <本次 configure 日志>
```

命中后**必须**再判消费面，才能决定是返工还是如实申报：

```sh
grep -rn HAVE_STRCASECMP <上游源码目录>   # 逐个宏数消费点
grep -rn HAVE_ALARM      <上游源码目录>
```

## 4. 已尝试并被推翻的结论（旧稿的错误，别再照抄）

1. **旧结论**：混配（conan automake/1.18 的 aclocal 宏 + 本机 autoconf 2.72）导致错序，同族配对则顺序正常。
   **推翻证据（单变量对照，15 行 configure.ac，不编译、不占构建槽）**：
   | 组 | configure.ac 差异 | 首调用 | 首定义 | 定义块 | 结论 |
   |---|---|---|---|---|---|
   | P | 含 `PKG_CHECK_MODULES(ITL, libitl, [], [AC_CHECK_LIB(itl,getNorthQibla)])` | 1537 | 4594 | 2 | 错位 |
   | Q | 其余逐字相同，仅把该宏换成等价 `AC_CHECK_LIB` | 1568 | 1477 | 1 | 正常 |

   两组都用 autoconf 2.72 + automake 1.17 同族、都带 `ACLOCAL_PATH` 指向 pkg-config 0.29.2 的 `share/aclocal`。
   ⇒ 触发变量是 **`PKG_CHECK_MODULES` 宏展开本身**，与 automake 取哪个发布、是否与 autoconf 同族**无关**。
2. **旧结论引用的"好生成物"读数不成立**：旧稿拿"定义 1526 早于调用 1755"当作正常形态的证据。
   实测那份件是**未带 `ACLOCAL_PATH` 生成**的，`PKG_CHECK_MODULES` 原始宏文本仍留在其第 4658 行，
   `sh -n configure` 直接在 4658 行报 `syntax error: unexpected 'ITL,'` ⇒ 那份件根本跑不起来，
   不能证明任何"顺序正常"。**顺带纠正一条推论**：判断生成物是否可用，硬判据是 `sh -n configure` 通过，
   而不是函数行号先后。
3. **旧结论**：该错序会以 `configure: error: cannot guess build type; you must specify one` 收尾。
   本轮同族错位件在真机上 configure 退出 0、`conan create` rc=0 ⇒ 该文案只是**同一报错家族里的另一种下游**，
   不是本条的必要后果（看到它仍应先按 E007/E072/E160 的老 config.guess 族判，再回过来查本条）。

## 5. 最终方案与真实验证

本条给的是**申报与判定纪律**，不是把 configure 修好的魔法（生成物缺陷属 autoconf/pkg.m4 上游层）：

- **交付前把 configure 日志的 `command not found` 当硬查项**，命中即认定链接探测失真，再按 §3 的消费面分流：
  消费点为 0 ⇒ 产物行为无损，在 notes 与 PR 的已知限制里逐条列明"哪些探测假失败 + 判据是消费点为零"；
  消费点非 0 ⇒ **不得照原样交付**，需消除 `PKG_CHECK_MODULES` 这条展开路径（改显式 `AC_CHECK_LIB` +
  `AC_CHECK_HEADERS` 组合），改完用 §3 复测定义回到调用之前才算修好。
- **真实验证（本包 2026-09-29）**：随包导出的 configure 定义 4831 / 首调用 1724 ⇒ 命中；日志 4 处 command not found；
  `config.h` 的 `HAVE_ALARM`、`HAVE_STRCASECMP` 为未定义形态；上游 ical.c / idate.c / ipraytime.c 对这三个宏
  **引用数均为 0**（全包条件编译仅 5 处，只消费 `TM_IN_SYS_TIME` 与 `HAVE_TM_GMTOFF`）⇒ 判定为**产物行为无损**，
  按如实申报交付；同轮 `test_package` 12 条行为断言全部通过（含回历↔公历往返闭合，证 libitl 真被链上算对）。
- **不要用 `ac_cv_*` 缓存或预设 `cross_compiling` 盖掉**（forbid_1）：错位定义是生成物损坏，缓存只会把探测结论换成人为设定。
- **不要顺手加 `--build/--host` 三元组当解法**（forbid_2）：那是 E007 家族的解法，与本轮实测退出 0 的成因不同。

## 6. 适用范围、反例与解除条件

- 适用：`configure.ac` 含 `PKG_CHECK_MODULES` 且由 autoconf 现场自举的 autotools 包。
- 不适用（反例）：tarball 自带 configure 且配方不自举的包；只用 `AC_CHECK_HEADERS`/`try_compile` 类探测的包；
  §4 表里的 Q 组形态（等价 `AC_CHECK_LIB` 写法）本身正常。
- 与本条正交的一件事：**CI worker 缺 host autotools**（本例实测 worker 有 hnp autoconf 2.72 但 `aclocal` 不可用，
  构建期 autoreconf 直接 `Can't exec "aclocal"` exit 2）⇒ 解法是随包导出预生成件、构建期零 bootstrap，
  形态照已合入的 libxmi/1.2（compat/）与 afflib/3.7.22（generated/）。
  **注意这条导出形态不修复本条的探测失真**——错位定义被原样带过去，仍要走 §3 判定。
- 解除条件：autoconf 或 pkg.m4 升级后 §3 的 `d > u` 不再成立，则本条解除，降级为普通探测记录。

## 7. 查重结论与新增价值

- 知识库既有 E007 / E072 / E160 覆盖的是"老 config.guess 不认识 HarmonyOS ⇒ cannot guess build type"，解法为显式三元组；
  E232/E467/E540 覆盖 configure 参数与 LIBS 注入面。**"链接探测因生成物错位而静默假失败、且构建全绿"这一形态在库内零命中**。
- 新增价值在于它是**一类会被全绿掩盖的失真**：给出两条 30 秒只读判据（行号先后 + 消费点计数）与明确的分流规则，
  可直接被任何 autotools 包 PR 复用；并留下一条通用副产物——判断 autotools 生成件可用性用 `sh -n`，不要用行号先后。
- 最小复现 15 行、无需编译器与构建槽，任何窗口都能一次跑完复核。
