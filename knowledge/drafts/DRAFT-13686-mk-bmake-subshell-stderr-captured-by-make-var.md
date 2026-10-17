# DRAFT-13686-mk-bmake-subshell-stderr-captured-by-make-var

> Status: **Draft**（待审核 promote）| severity: `2` | category: `compat|portability|testing|build-system` | Updated: 2026-09-29
> 对应: `knowledge/drafts/DRAFT-13686-mk-bmake-subshell-stderr-captured-by-make-var.kv`
> 来源: mk（mk-configure）0.40.0 适配 OHOS，PR #13686
> 修正记录: v2 — 初稿误称"bmake 把 stderr 并入变量值"，经 W4 独立审计实测**证伪**后按真实现象改写（见「根因」）

**匹配关键词**：bmake, NetBSD make, `!=` assignment, command substitution, stderr folded by 2>&1, test_output, expect.out, minitest, mkc.minitest.mk, id -un, "returned non-zero status", diff mismatch, HarmonyOS, OPSYS, 批量用例同时失败

## 现象

mk-configure 0.40.0 在 OHOS 上跑上游回归测试时，**一批看似无关的用例同时 FAILED**，且被 diff 的实际输出里混入与用例内容无关的两行（下为真实捕获形态）：

```text
=========== all ============
sh: id: inaccessible or not found
warning: "id -un" returned non-zero status
sh: id: inaccessible or not found
warning: "id -gn" returned non-zero status
BUILTIN.endianness=big
```

**经证据筛选**：在 `mk-0.40.0-build/logs/09-test-full.log`（修复前全量）中，diff 的**实际侧**（`>` 行）确实出现上述噪音且判定 FAILED 的用例**至少 7 个**（下表为可逐行核对的证据；同一日志中 `examples/requirements` 等用例的 diff 亦出现同类噪音行）：

| 用例 | diff 实际侧含噪音行数 |
|---|---|
| `tests/predopost_targets` | 70 |
| `tests/cccxx_type` | 31 |
| `tests/endianness` | 2 |
| `tests/require_prototype` | 2 |
| `tests/reqd_clean_cache` | 2 |
| `tests/test_subprj_dash` | 1 |
| `tests/FSRCDIR` | 1 |

它们与被测功能毫无共同点，唯一的共性是"对内层 make 做了 `2>&1` 折流后比对文本"（复现命令：`grep -n '2>&1' tests/*/test.mk`）。
`examples/customtests2` 也收到了噪音但**未因此失败**（噪声落在其期望之外的位置）。

> ⚠️ **勿与同批其他失败混淆**（这是本条的诊断要点）：同一轮里
> `tests/mkshlib` / `mkstaticlib` / `mkpiclib` / `mkprofilelib` / `mkdll` 的失败源于**无 chown 的用户盘导致安装中止**（见姊妹草稿 `DRAFT-13686-mk-ohos-shell-alias-breaks-exec-probe`）；
> `tests/mkc_features` 源于 **libc 无 `fts_*`**；`tests/FSRCDIR` 另有**设备缺 `automake`** 的叠加原因；
> `examples/subdirs`（含 `prog1`/`prog2`）同为**安装中止类**（该节含 4 行 `chown: inaccessible or not found`：prog1=3 + prog2=1；diff 缺 `bin/prog1`、`bin/program1.awk`、`libexec/program1.sh`、`bin/program2`），由补丁 0002 修复。
> 把它们与本条混为一谈会误导修复方向。

## 根因（v2 已按实测修正）

**第一步（澄清一个常见误判）**：bmake 的 `!=` **并不**捕获 stderr，与 GNU make 的 `$(shell)` 一致。实测（bmake 20200710）：

```console
$ printf 'X != sh -c '"'"'echo STDOUT_ONLY; echo STDERR_TEXT 1>&2; exit 1'"'"'\nall:\n\t@echo "X=[${X}]"\n' > b.mk
$ bmake -r -f b.mk -V X
STDOUT_ONLY                      # ← stderr 不进入变量值
$ make  -f g.mk -s               # GNU make $(shell …) 同结果
X=[STDOUT_ONLY]
```

**第二步（真实链路，两跳）**：

1. 探测命令在 OHOS 上失败——设备用户库不含构建 uid（`/system/bin/id -u` → `id: bad uid 20020084`，`sh` 中 `id` 不可达）。`mk/mkc.init.mk` 的 `_MKC_USER != ${ID:Uid} -un` 因此让 **bmake 自身**向 stderr 打印两行：
   `sh: id: inaccessible or not found` 与 `warning: "id -un" returned non-zero status`（**不在变量值里**）。
2. 测试配方惯用 `${MAKE} <target> 2>&1 | ...` 把内层 make 的 stderr 与 stdout **折成同一流**。本例 46 个 tests 用例中 **18 个含 `2>&1`**（如 `tests/endianness/test.mk:8`、`tests/FSRCDIR/test.mk:6`），于是这两行随 stdout 被 `mk/mkc.minitest.mk` 的 `test_output` 捕获进 `*.test.out`，`diff expect.out` 判定失败。

可复现试验（不需要改动被测工程）：

```console
$ printf 'ID = id\n.if ${ID} != "@ID@"\n_MKC_USER != ${ID:Uid} -un\n.endif\nshowme:\n\t@echo "U=[${_MKC_USER}]"\n' > d.mk
$ bmake -r -f d.mk showme 2>&1
sh: id: inaccessible or not found
bmake: "d.mk" line 3: warning: "id -un" returned non-zero status
U=[]
$ bmake -r -f d.mk showme 2>/dev/null
U=[]                            # ← 不折流时两行不进入 stdout
```

**诊断陷阱**：失败信息里看不到"这 8 个用例为什么一起失败"，逐个排查代价极高。

## 解决方案

对可能失败的探测命令**同时**静默 stderr **并**把退出码归零（推荐方案 `silence-probe-stderr-and-neutralize-exit`）：

```make
.if ${ID} != "@ID@"
# HarmonyOS/OHOS 的用户库可能不含构建 uid，id(1) 会失败。保持静默且不产生非零退出：
# 失败的 id(1) 既不应中断构建，也不应经测试配方的 2>&1 污染被 diff 的输出。
_MKC_USER   !=	${ID:Uid} -un 2>/dev/null || true
_MKC_GROUP  !=	${ID:Uid} -gn 2>/dev/null || true
.endif
```

二者缺一不可：
- `2>/dev/null` 去掉 `sh: id: inaccessible or not found`；
- `|| true` 让命令以 0 退出，bmake 不再打印 `warning: "id -un" returned non-zero status`。

**验证**（修复后，最终干净树全量逐例执行 `mk-0.40.0-build/logs/29-final-cases.log`）：
上列 7 个用例**全部 exit=0（PASS）**，同轮其余用例亦全绿（全量 109 例 89 PASS / 20 FAIL，FAIL 均为设备/平台缺口）：

```text
test-tests/predopost_targets   exit=0      test-tests/reqd_clean_cache   exit=0
test-tests/cccxx_type          exit=0      test-tests/test_subprj_dash   exit=0
test-tests/endianness          exit=0      test-tests/FSRCDIR            exit=0
test-tests/require_prototype   exit=0
```

（注：`FSRCDIR` 除本条的噪音外还叠加了设备缺 `automake`——安装 `automake/1.18` 与 `autoconf/2.72` 后在最终树通过。）

## 禁止策略

| 禁止 | 原因 | 后果 |
|---|---|---|
| 只写 `2>/dev/null` 不把退出码归零 | bmake 仍打印 `warning: "..." returned non-zero status`，该 warning 同样经配方 `2>&1` 折入被 diff 的输出 | 测试仍 FAILED，报错形态变化更难定位 |
| 把报错行加进 `expect.out` | 把环境相关文本固化为期望 → 掩盖真因，换机器/换用户即碎 | 用例丧失回归价值，评审驳回 |

## 适用范围

所有以 **bmake/NetBSD make** 驱动、且测试配方对内层 make 做 `2>&1` 折流后比对文本期望的工程：mk-configure 系（`mk/mkc.minitest.mk`）、BSD 源码树回归测试（NetBSD/FreeBSD/OpenBSD 的 `tests/` 惯例）。
触发条件是**探测命令本身会失败**，不限于 `id`——`uname`、`which`、`pkg-config --version` 等在受限平台上失败时同构。

## 关联

- `P013`（平台限制必须降级而非绕过）、`P014`（环境变量与构建系统语义冲突陷阱）
- 与 `E002`（`/tmp` 只读 → 设 `TMPDIR`）、`E046`（HMDFS `chmod` 不生效）同属"OHOS 环境事实导致上游假设不成立"，但本条入口是**测试捕获链路上的 stderr 折流**，与前两者的文件系统入口不同
- 修复补丁：`archives/m/mk/0.40.0/patches/0001-ohos-platform-support.patch`
