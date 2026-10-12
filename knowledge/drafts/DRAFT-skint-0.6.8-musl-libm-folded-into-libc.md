# DRAFT-skint-0.6.8: OHOS musl 把 libm 折叠进 libc.so（DT_NEEDED 只有 libc.so）

Status: DRAFT
Source: skint 0.6.8（false-schemers/skint，tag v0.6.8）
PR: 【知识库扩展】feat(skint): 0.6.8 适配 HarmonyOS PC（分支 feat/skint-0.6.8）

## 相关既有条目

撞库命令与结果（2026-10-02）：

```
python3 scripts/ohc-run.py engine "musl libm 折叠 libc DT_NEEDED libm.so.6"   -> E401（MLton golden 的 libm 舍入差异，非依赖关系）
grep -Ein "libm.so|DT_NEEDED|NEEDED" knowledge/graph/index.tsv               -> 无“libm 折叠进 libc”条目
grep -REil "folds libm|libm 并入|libm.so.6" knowledge/doc/                    -> 仅 E401（浮点舍入），机制无关
```

| 条目 | 已覆盖内容 | 本草稿增量 |
|---|---|---|
| E401 | OHOS musl libm 的**舍入行为**与 glibc golden 差 1 ULP（MLton real 回归） | E401 是**数值语义**差异；本条是**链接/依赖模型**差异：sysroot 无 libm.so、-lm 由空壳满足、DT_NEEDED 只剩 libc.so |
| P012 | 静态库优先、系统同名库冲突防护 | 本条给出该原则在“libm 这类被折叠进 libc 的系统库”上的可执行判据 |
| E029/E135 族（签名/加载） | ELF 签名与加载行为 | 与本条无关，仅检索留痕 |

结论：现有条目未覆盖“libm 在 OHOS 上不是独立共享库”这一模型，可独立申报；相近条目填 `similar_to: E401`。

## Scope

适用：

- 在 OHOS（musl sysroot）上构建、并链接了 `-lm` 或声明 `system_libs=["m"]` 的库/可执行文件；
- 按 glibc 习惯写 ELF/打包断言（检查 `libm.so` / `libm.so.6` 是否在 `DT_NEEDED`）的
  `test_package`、L2/L4 类门禁、审计脚本。

不适用：glibc 目标的 aarch64/x86_64 构建（那里 `libm.so.6` 确实独立存在，`-lm` 会产生真实依赖）。

## Symptom

用 OHOS SDK 交叉编译一个同时链接 `-lm` 的程序，产物 `DT_NEEDED` 里**没有** libm：

```
$ ls -l $OHOS_SYSROOT/usr/lib/aarch64-linux-ohos/libm.*
-rw-r--r--  1 ...  88  libm.a            # ← 88 字节；ar t 只有 __.SYMDEF（空壳）
# 没有 libm.so，也没有 libm.so.6

$ printf 'int main(void){return 0;}\n' > /tmp/lmprobe.c
$ <ohos-clang> -o /tmp/lmprobe /tmp/lmprobe.c -lm
$ llvm-readelf -d /tmp/lmprobe | grep NEEDED
  0x0000000000000001 (NEEDED)  Shared library: [libc.so]      # ← 仅 libc.so
```

同一现象出现在真实软件上：skint 0.6.8 的 makefile 链接 `-lm`，打包产物的
`DT_NEEDED` 仍是 `[libc.so]`（skint 归档 `test_package/ohos_abi_check.py` 的 A3 断言）。

反向误区：若按 glibc 习惯断言“`-lm` 必须带来 `libm.so.6`”，在 OHOS 真机上会得到**假失败**，
并被误判为“缺库/依赖没打进去”。

## Root Cause

musl 把数学库实现放在 libc 实现内部：OHOS SDK 的 aarch64-linux-ohos sysroot 里
`libm.so` / `libm.so.6` 都不存在，只留一个 88 字节的 `libm.a`（`ar t` 只有 `__.SYMDEF`，
即空归档）。于是：

- `-lm` 由这个**静态空壳**满足，不产生 `DT_NEEDED` 条目；
- 数学符号在运行时由 `libc.so` 提供（libc 里已含实现）；
- 因此“链接 `-lm` ⇒ `DT_NEEDED` 含 libm”这一 glibc 经验在 OHOS 上不成立。

这不是缺库，也不是打包漏文件，而是**libc 布局差异**。

## Recommended Fix / Workaround

1. 把 OHOS 侧的 ABI 期望改成 **libc-only**：

```python
EXPECTED_NEEDED = ["libc.so"]           # aarch64-linux-ohos
assert sorted(needed) == EXPECTED_NEEDED
```

   若不便断言全集，至少断言“不含 glibc 专属 SONAME”（`libm.so*`、`libc.so.6` 等）。

2. 把这条**当正向判据**用：一个链接了 `-lm` 的程序若 `DT_NEEDED` 恰为 `[libc.so]`，
   就说明它确实是用 OHOS musl sysroot 构建的（glibc aarch64 产物会多出 `libm.so.6`）。
   skint 归档把这做成 `test_package/ohos_abi_check.py` 的 A3，与 A2（`.interp ==
   /lib/ld-musl-aarch64.so.1`）互为交叉验证。

## Fallback

不便断言 `DT_NEEDED` 全集时，至少断言 `.interp`：

```bash
llvm-readelf -l <artifact> | grep -A1 INTERP     # 期望 /lib/ld-musl-aarch64.so.1
```

`.interp` + “无 libm.so.6” 两条合起来，足以把 OHOS musl 构建和其他 aarch64 Linux 构建区分开。

## Forbidden Approaches

| 禁止写法 | 原因 | 后果 |
|---|---|---|
| `cp/link libm.so` 到 `/lib` 或 sysroot | sysroot 的 libm.a 是空壳，系统也没有 libm.so；自造同名库属 R26 系统同名库污染 | 影响其他应用/系统组件加载 |
| `-Wl,--no-as-needed` 等强行制造 libm 依赖 | 只为让 `DT_NEEDED` “看起来像 glibc” | 暴露假依赖，掩盖真实的 libc-only 事实 |
| ABI 断言里写死 `libm.so`/`libm.so.6` 存在 | glibc 判据在 OHOS 不成立 | 真机假失败，误导排查方向 |

## Verification

```bash
# A) sysroot 事实
ls -l "$OHOS_SYSROOT/usr/lib/aarch64-linux-ohos/"libm.*
ar t "$OHOS_SYSROOT/usr/lib/aarch64-linux-ohos/libm.a"      # 仅 __.SYMDEF

# B) 最小探测：-lm 不产生 libm 依赖
printf 'int main(void){return 0;}\n' > /tmp/lmprobe.c
<ohos-clang> -o /tmp/lmprobe /tmp/lmprobe.c -lm
llvm-readelf -d /tmp/lmprobe | grep NEEDED                  # 仅 libc.so

# C) 真实产物复核（skint 0.6.8 打包产物）
llvm-readelf -d <pkg>/bin/skint | grep NEEDED                # 仅 libc.so
python3 test_package/ohos_abi_check.py --binary <pkg>/bin/skint   # A3_musl_libm_folded PASS
```

## Prevention

- 写 ABI/打包断言前，先看一眼目标 sysroot 的库清单（`ls` + `ar t`），不要照搬 glibc 的 SONAME 集合。
- 把“OHOS 侧 `DT_NEEDED` 只应出现 libc.so（个别系统库除外）”写成 test_package 的固定检查项，
  与 `.interp` 一起作为“是否真的用 OHOS musl sysroot 构建”的证据。
- 需要数学库时正常写 `-lm` / `system_libs=["m"]` 即可，**不要**为它准备或投放任何 `.so`。

## References

- OHOS SDK sysroot：`$OHOS_SYSROOT/usr/lib/aarch64-linux-ohos/{libc.so,libm.a}`
- skint 归档证据：`archives/s/skint/0.6.8/test_package/ohos_abi_check.py`（A2/A3）、
  `archives/s/skint/0.6.8/notes.md`（musl 判据小节）
- 同族：`E401`（musl libm 舍入差异）、`P012`（静态库/系统同名库防护）
