# DRAFT-ctags-6.2.1.1-hmdfs-mktemp-AS_TMPDIR-unwritable：HMDFS 上 `mktemp -d` 目录不可写，autoconf AS_TMPDIR 失败

> Contributor: OpenDesk | Status: Draft | Updated: 2026-09-26
> Source: ctags 6.2.1.1 适配 HarmonyOS PC（目标库任务）
> 对应：`knowledge/drafts/DRAFT-ctags-6.2.1.1-hmdfs-mktemp-AS_TMPDIR-unwritable.kv`

## 使用说明（怎么用这条知识）

1. 在 HarmonyOS 上跑 autotools 的 `configure`，若看到：
   ```text
   ./config.status[1491]: can't create ./confXXXXXX/subs1.awk: Permission denied
   config.status: error: could not setup config files machinery
   ```
   或 `config.guess` / 其他构建脚本报 `can't create .../cgXXXXXX/dummy.c: Permission denied`，
   即命中本模式。
2. 用下方"定性三步"确认根因（**不要直接 chmod，也不要相信 `test -w`**）。
3. 按"修复方案"把 `configure`（及它写出的 `config.status` 模板）的 `mktemp -d` 优先分支替换为 `mkdir`。

## 适用范围

任何在 HMDFS 工作目录下调用 `mktemp -d` 后**向该目录写文件**的构建逻辑：

| 场景 | 具体位置 |
|------|---------|
| autoconf 生成/运行的 configure | `AS_TMPDIR`（`./confXXXXXX`），以及它写入 `config.status` 的同一段模板 |
| GNU config.guess / config.sub | `set_cc_for_build`（`$TMPDIR/cgXXXXXX`） |
| 自定义构建脚本 | 任何 `tmp=$(mktemp -d)` 后 `> $tmp/...` |

工作目录位于 HMDFS（OHOS 上用户目录、`~/tmp`、项目目录通常如此）时命中。

## 输入 / 输出定义

| 项 | 定义 |
|----|------|
| 输入 | 可写的 `configure`（及生成 `config.status` 的模板段）；HMDFS 上的工作目录 |
| 输入前置 | `ls -ld <mktemp目录>` 显示 `drwx--S---`(2700)；`chmod 777` 后权限位不变；`test -w` 为真但写入失败 |
| 输出 | `AS_TMPDIR` 处改为 `mkdir` 路径（无 `mktemp -d`）；configure 与 config.status 阶段临时目录均可写 |
| 成功后状态 | `configure` 退出码 0；日志出现 `config.status: creating Makefile` 等 |
| 失败信号 | 仍出现 `can't create ./confXXXXXX/...` 或 `could not setup config files machinery` |

## 定性三步（关键：环境会"骗人"）

```bash
# ① 目录名形态：confXXXXXX / cgXXXXXX ⇒ mktemp 模板
# ② 实测权限（在 .work 源码目录内）
tmp=$( (umask 077 && mktemp -d "./confXXXXXX") ); ls -ld "$tmp"
#   → drwx--S--- 2 <service-owner> <group>   ← 2700，group/other 无权限
# ③ chmod 与 test -w 都会给出错误结论
chmod 777 "$tmp"; ls -ld "$tmp"     # 权限位不变（HMDFS 忽略 chmod）
test -w "$tmp" && echo WRITABLE     # 打印 WRITABLE，但下一行失败：
echo hi > "$tmp/x"                  # → Permission denied
# 对照：mkdir 路径可用
mkdir -p ./conf-mkdir-test && ls -ld ./conf-mkdir-test   # drwxrws--x（2771，group 可写）
```

## 修复方案（最小补丁）

`configure` 中（以及它输出到 `config.status` 的同一段模板）：

```diff
 # Create a (secure) tmp directory for tmp files.
-
-{
-  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
-  test -d "$tmp"
-}  ||
 {
   tmp=./conf$$-$RANDOM
   (umask 077 && mkdir "$tmp")
 } || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5
 ac_tmp=$tmp
```

要点：
- **必须两处都改**：configure 主体与 config.status 模板是两段独立文本。自检：
  ```bash
  grep -c 'confXXXXXX' configure config.status    # 都应为 0
  ```
  （只改一处时，重跑 configure 后仍会在 `config.status` 阶段失败——本包实测踩过。）
- 不要试图用 `chmod` 或 `test -w` 分支补救（在此文件系统上双双失效）。
- 若同样的 `mktemp -d` 出现在 `config.guess` 的 `set_cc_for_build` 中，优先用"平台分支提前 return"绕开（见姊妹条目），避免额外改 config.guess。

## 示例（ctags 6.2.1 实测）

```text
# 修复前
$ ./configure --prefix=$PREFIX
...
config.status: creating Makefile           ← 前面检测全部 OK
./config.status[1491]: can't create ./confLGOKhp/subs1.awk: Permission denied
config.status: error: could not setup config files machinery

# 修复后
$ ./configure --prefix=$PREFIX
checking build system type... aarch64-unknown-linux-ohos
config.status: creating Makefile
config.status: creating gnulib/Makefile
config.status: creating config.h
configure exit=0
```

补丁文件（本仓库）：`archives/c/ctags/6.2.1.1/patches/0002-configure.patch`（+6/-5 行）。

## 相关平台知识

- E046：HMDFS 上 `chmod` 不生效（SELinux/服务账户语义）。
- E002：`/tmp` 只读，需用 `$TMPDIR`（本项目为 `~/tmp`）。
- 进程与文件 owner 不一致：文件 owner 固定为 `file_manager` 服务账户，权限判断走 group/other 位。
