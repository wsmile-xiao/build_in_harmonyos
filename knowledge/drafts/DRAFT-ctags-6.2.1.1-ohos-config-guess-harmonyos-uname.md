# DRAFT-ctags-6.2.1.1-ohos-config-guess-harmonyos-uname：HarmonyOS 的 uname -s 返回 HarmonyOS，autotools config.guess 猜不出三元组

> Contributor: OpenDesk | Status: Draft | Updated: 2026-09-26
> Source: ctags 6.2.1.1 适配 HarmonyOS PC（目标库任务）
> 对应：`knowledge/drafts/DRAFT-ctags-6.2.1.1-ohos-config-guess-harmonyos-uname.kv`

## 使用说明（怎么用这条知识）

1. 在 HarmonyOS/OpenHarmony 上跑 `./configure`，若看到：
   ```text
   configure: error: cannot guess build type; you must specify one
   ```
   即命中本模式。
2. 先做定性确认（30 秒）：
   ```bash
   uname -s          # 期望输出 HarmonyOS（不是 Linux）
   ./config.guess    # 期望 exit≠0，stderr: unable to guess system type
   ```
3. 按下方"修复方案"给 `config.guess` 打最小补丁，然后重跑 `./config.guess` 与 `./configure` 验证。

## 适用范围

- 使用 autoconf/autotools 且依赖 `config.guess` 的项目（`AC_CANONICAL_BUILD/HOST/TARGET`）。
- 在平台 `uname -s` 不等于 `Linux` 时（本平台为 `HarmonyOS`）。
- 典型分发形态：release tarball 内置预生成 `configure`（无需 autoreconf）。
- 反例（不在本模式范围）：`config.sub` 报错 `Invalid configuration ...` ⇒ 那是三元组校验问题，见备注。

## 输入 / 输出定义

| 项 | 定义 |
|----|------|
| 输入 | 上游源码树中的 `config.guess`（可写）；平台 `uname` 输出 |
| 输入前置 | 确认 `uname -s` == `HarmonyOS`；确认 `config.sub` 已支持 `ohos*`（≥2024-05-27 版本即可） |
| 输出 | `config.guess` 新增 `*:HarmonyOS:*:*` 分支；`./config.guess` 输出 `<machine>-unknown-linux-ohos` |
| 成功后状态 | `configure` 打印 `checking build system type... aarch64-unknown-linux-ohos` 并继续 |
| 失败信号 | 仍报 `cannot guess build type`；或 `config.sub` 报 `Invalid configuration 'aarch64-unknown-linux-ohos'` |

## 修复方案（最小补丁）

在 `config.guess` 的 case 语句**最前面**插入（补丁新增行）：

```sh
case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in
    *:HarmonyOS:*:*)
	# OpenHarmony: uname reports "HarmonyOS" as the system name rather
	# than "Linux".  Map the reported machine to the OHOS OS triple.
	case $UNAME_MACHINE in
	    armv7* | armv8* | arm*) GUESS=arm-unknown-linux-ohos ;;
	    aarch64* | arm64*)      GUESS=aarch64-unknown-linux-ohos ;;
	    x86_64 | amd64)         GUESS=x86_64-unknown-linux-ohos ;;
	    i?86)                   GUESS=i686-unknown-linux-ohos ;;
	    *)                      GUESS=$UNAME_MACHINE-unknown-linux-ohos ;;
	esac
	;;
    *:NetBSD:*:*)          # ← 原有分支，保持不动
	...
```

要点：
- 分支放在**最前**，避免落入 NetBSD/Linux 等既有分支。
- 该分支不做编译器探测（不调用 `set_cc_for_build`），因此**顺带规避** HMDFS 临时目录问题。
- 补丁不含任何平台宏（不用 `#ifdef`），纯 shell case 匹配。

## 示例（ctags 6.2.1 实测）

```text
# 修复前
$ ./config.guess
./config.guess[1741]: can't create /storage/.../tmp/cgcNAoHl/dummy.c: Permission denied
./config.guess: unable to guess system type
config.guess timestamp = 2024-07-27
uname -m = aarch64
uname -s = HarmonyOS
...
$ ./configure --prefix=$PREFIX
configure: error: cannot guess build type; you must specify one

# 修复后
$ ./config.guess
aarch64-unknown-linux-ohos
$ ./configure --prefix=$PREFIX
checking build system type... aarch64-unknown-linux-ohos
...
config.status: creating Makefile
```

补丁文件（本仓库）：`archives/c/ctags/6.2.1.1/patches/0001-config.guess.patch`（+12 行）。

## 常见误判

| 误判 | 为什么错 |
|------|---------|
| 用 `--build=aarch64-unknown-linux-ohos` 传参解决 | 掩盖识别缺陷，不产生可复用知识，下游包逐个传参不可维护（本仓库规约禁止） |
| 把 config.guess 整体替换成"已知可用版本" | 上游版本可能更新，整体替换引入大量无关 diff（ctags 历史归档踩过：用 2023 版替换 2024 版） |
| 认为 `config.sub` 也要改 | config.sub ≥2024-05-27 已接受 `ohos*` / `linux-ohos*`，通常无需改动 |
| 把 `can't create .../cgXXXXXX/dummy.c: Permission denied` 当作独立问题 | 它是 HMDFS 临时目录问题（见姊妹条目），补上 HarmonyOS 分支后自然消失，但若其他路径仍报，需另行修复 |
