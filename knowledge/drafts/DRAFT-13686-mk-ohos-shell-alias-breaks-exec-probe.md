# DRAFT-13686-mk-ohos-shell-alias-breaks-exec-probe

> Status: **Draft**（待审核 promote）| severity: `3` | category: `compat|portability|shell|installation` | Updated: 2026-09-29
> 对应: `knowledge/drafts/DRAFT-13686-mk-ohos-shell-alias-breaks-exec-probe.kv`
> 来源: mk（mk-configure）0.40.0 适配 OHOS，PR #13686
> 修正记录: v2 — 精确化别名范围（实测）并订正退出码/引用日志

**匹配关键词**：command -v, alias, toybox applet, OHOS /bin/sh, alias table, chown, chgrp, set -e, exec probe, package install, silent abort, files not installed, mkc_install, rc=127

## 现象

mk-configure 的安装型用例（`tests/mkshlib`、`mkstaticlib`、`mkpiclib`、`mkprofilelib`、`mkdll`）失败，错误信息只有一行，且 diff 显示**目标文件根本没安装**：

```text
mkc_install[169]: chown: inaccessible or not found
*** Error code 1
```

```diff
--- expect.out
+++ mkshlib.test.out
 ========= install ==========
 /objdir/prefix
 /objdir/prefix/include
- /objdir/prefix/include/hello_msg.h
 /objdir/prefix/include/impl
- /objdir/prefix/include/impl/hello_msg1.h
- /objdir/prefix/include/impl/hello_msg2.h
 /objdir/prefix/lib
- /objdir/prefix/lib/libcxxlib.a
```

即：目录建出来了，**文件一个都没落地**，而脚本本身"看起来"只是抱怨了一下 `chown`。更反直觉的是探测阶段认为 `chown` 是**存在**的：

```console
$ sh -c 'command -v chown; echo "rc=$?"'
alias chown=chown
rc=0
$ sh -c 'chown --help'; echo "rc=$?"
/usr/bin/sh: chown: inaccessible or not found
rc=127
```

## 根因

1. **OHOS 的 `/bin/sh` 启动时预置 **139** 条 toybox 别名**（实测 `sh -c 'alias' | grep -c .`）。`command -v` 对别名表内的名字返回 `alias X=X`——**非空、非路径、rc=0**：

   | 命令 | `command -v` 输出 | rc | 备注 |
   |---|---|---|---|
   | `chown` / `chgrp` | `alias chown=chown` / `alias chgrp=chgrp` | 0 | 别名表内，**假阳性** |
   | `chmod` / `cp` / `mv` / `mkdir` / `rm` / `sed` / `awk` | 同名 `alias X=X` | 0 | 别名表内；因在 PATH 中存在而无害 |
   | `ln` / `expr` / `nm` / `strip` | 绝对路径 | 0 | 非别名 |
   | `id` / `install` | 空 | 1 | 不在别名表，判定正确 |

2. 于是以"`command -v` 有输出 → 程序存在"判定可用性得到**假阳性**；真正调用时若该名字**不在 PATH**（本机 `/system/bin` 不在 PATH），shell 报 `inaccessible or not found` 并返回 **127**。
3. mk-configure 的 `scripts/mkc_install`（源自 X11R5 `install.sh`）以 `set -e` 运行，`copy_file()` 顺序为：

```sh
$doit $instcmd "$src" "$dsttmp"     # cp 成功
$doit $chowncmd "$dsttmp"           # chown 失败(127) → set -e 立即中止
...
$doit $mvcmd "$dsttmp" "$dst"       # 永不执行
```

`cp` 成功、`chown` 失败即整体中止，`mv` 不执行，且入口 `trap "rm -f ${dsttmp}" 0` 还会删掉临时文件——**文件静默不落地**。目录之所以存在，是此前 `-d` 分支逐个建成后同样中止。

## 解决方案

把 `command -v` 的结果**解析为绝对路径后再判可执行**，解析不到就回退为空操作（推荐方案 `resolve-absolute-then-test-x`）：

```sh
chownprog="${CHOWNPROG-chown}"
chgrpprog="${CHGRPPROG-chgrp}"

# chown(1)/chgrp(1) 并非所有平台都有（HarmonyOS/OHOS 只提供无法执行的 shell 别名）。
# 除非能解析出可执行文件，否则回退 ":"，避免 set -e 下安装中止、文件不落地。
_mkc_chown=`command -v "$chownprog" 2>/dev/null` || _mkc_chown=
test -x "$_mkc_chown" || chownprog=":"
_mkc_chgrp=`command -v "$chgrpprog" 2>/dev/null` || _mkc_chgrp=
test -x "$_mkc_chgrp" || chgrpprog=":"
unset _mkc_chown _mkc_chgrp
```

**验证**（修复后）：
- 安装树完整落地：`bmake install PREFIX=<prefix>` 后 `<prefix>/` 下 **214 个文件 / 4 个顶层目录**（`bin`、`libexec`、`share`、`man`），日志 `mk-0.40.0-build/logs/17-all-prefix.log`
- 5 个安装型用例在最终干净树全量逐例执行中**全部 exit=0（PASS）**：`mk-0.40.0-build/logs/29-final-cases.log`

```text
test-tests/mkshlib         exit=0      test-tests/mkprofilelib    exit=0
test-tests/mkstaticlib     exit=0      test-tests/mkdll           exit=0
test-tests/mkpiclib        exit=0
```

- 安装后系统可用：`conan create` exit=0；`test_package/test.sh` 用包内 `mkcmake` 构建并运行 C 程序 → `hello-from-mkcmake`（`mk-0.40.0-build/wt-logs/conan-create-testfix.log`）

## 禁止策略

| 禁止 | 原因 | 后果 |
|---|---|---|
| 以 `command -v` 的返回码/非空输出直接当"可执行"判据 | OHOS 别名表内的名字给出假阳性 | 后续执行 rc=127；`set -e` 脚本演变为静默中断 + 文件不落地 |
| 为了让脚本"不中断"而对安装步骤一律 `\|\| true` | 把残缺安装树伪装成成功 | 产出静默残缺的包——比显式失败危险得多（正是本条的原始症状） |

## 适用范围

所有在 OHOS 上做"程序可用性"探测并据此分支的 shell 脚本：安装脚本、构建系统探测、包管理器 wrapper。
**致命条件**：该名字**位于别名表内且不在 PATH**（在 PATH 时别名无害，展开后仍按 PATH 解析）。
同一陷阱不限于 `chown/chgrp`——别名表覆盖 `chmod/cp/mv/mkdir/rm/sed/awk/tar/grep/find` 等共 139 个名字，只要其不在 PATH 就会复现。

## 关联

- `P013`（平台限制必须降级而非绕过）—— 对策是"探测不到就安全跳过属主变更"，而不是绕过安装
- `E098`（OHOS `install`/toybox 命令缺失 → 替代方案）—— 本条补上 `command -v` **假阳性**这一更隐蔽的入口
- 修复补丁：`archives/m/mk/0.40.0/patches/0002-ohos-install-robustness.patch`
