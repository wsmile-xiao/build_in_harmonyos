# DRAFT-ohos-config-guess-third-form-branch-selfecho — config.guess 的第三形态（分支自行 echo+exit）

> Contributor: A4C8 / Status: **DRAFT** / Updated: 2026-09-16 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-config-guess-third-form-branch-selfecho`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `DRAFT-autotools-config-guess-two-generation-formats` | 草稿 | config.guess/config.sub 的**两代格式**差异（旧版 `GUESS=` / 新版 `set_cc_for_build`），patch 锚点须按代选择 | 那条给出**二分法**；**本条的要点是"二分法不够"** —— 实测存在**第三形态**（既无 `GUESS=`、又含 `set_cc_for_build`、输出靠分支自行 `echo`），按"有 `set_cc_for_build` 即新版"判会**误判并打空** |
| `scripts/patch-autotools-ohos.pl` | 仓内脚本 | 按新版锚点（`__ANDROID__`/`LIBC=android`、`android-linux`、`linux-uclibc`）打补丁 | 实测对该形态**只打中 1/5**（输出 3 条 `Could not find ...` warn + `Score: 1/5`）|

**全库查证**：`exit ;;` 作判据的条目命中 3 处、`echo ${UNAME_MACHINE}-unknown-linux` 仅 1 处（即本轮新增）；**无**条目指出"第三形态/三分法"。

## Scope（何时用）

**早期 autotools 工程**（2018–2020 世代发行版 tarball）在 OHOS 上适配
`config.guess`/`config.sub`。实测样本：**libpwquality 1.4.5**
（`timestamp='2018-08-29'`）。

## Symptom

### 表象一：patch"成功"但 config.guess 仍失败

```console
$ perl scripts/patch-autotools-ohos.pl config.guess config.sub
  [warn] Could not find __ANDROID__/LIBC=android in config.guess
  [warn] Could not find android-linux in config.sub
  [warn] Could not find linux-uclibc pattern in config.sub
Patching config.guess...
  [ok] Added HarmonyOS system identification
Score: 1/5        ❌ Some patches may have failed.

$ sh ./config.guess
./config.guess: unable to guess system type
This script (version 2018-08-29), has failed to recognize the ...
```

### 表象二：config.sub 把**已识别**的 triplet 改坏

```console
$ sh ./config.sub aarch64-unknown-linux-ohos
aarch64-unknown-linux-gnu-ohos        ← 被错误规范化！
$ sh ./config.sub aarch64-linux-ohos
Invalid configuration `aarch64-linux-ohos': system `ohos' not recognized
```

## Root Cause

`config.guess` 的 OHOS patch 有已知二分法，但**存在第三形态**。三条判据必须**合看**：

| 判据 | 旧版（`GUESS=`） | 新版（`set_cc_for_build`） | **第三形态（本包）** |
|---|---|---|---|
| `grep -c '^GUESS='` | 有 | 无 | **0** |
| `grep -c set_cc_for_build` | 无 | 有 | **12**（⚠️ 与"新版"判据撞车）|
| 输出机制 | 末尾统一 `echo $GUESS` | 同左 | **各分支自行 `echo` + `exit ;;`**（实measure 231 处 `exit ;;`）|

**关键陷阱**：第三形态**也含 `set_cc_for_build`**，所以"有 `set_cc_for_build` 就是新版"
的判据会把它误判为新版，进而插 `GUESS=...` 赋值——但**该形态下无人 echo `$GUESS`**，
于是 patch 文本插入"成功"而**运行时毫无效果**。

`config.sub` 侧同理：该形态的 `linux-*` 模式列表更旧、无 `ohos`，需补
`linux-ohos*`，否则既报 `not recognized`，又会把 `...-linux-ohos` 错误规范化。

## Recommended Solution

### 主方案（priority 1）— 按形态插「自行 echo+exit」的分支

**`config.guess`**：在主 `case` 语句**起始处**（第一个分支之前）插入：

```sh
    *:HarmonyOS:*:*)
	echo ${UNAME_MACHINE}-unknown-linux-ohos
	exit ;;
```

**`config.sub`**：改**两处**（`maybe_os` 列表 + os 合法性列表），各加 `linux-ohos*`；
**插入行须带 `\` 续行符**，否则 case 语法错误：

```diff
-			| linux-newlib* | linux-musl* | linux-uclibc* | uclinux-uclibc* \
+			| linux-newlib* | linux-musl* | linux-uclibc* | linux-ohos* \
+			| uclinux-uclibc* \
```

**必须实测验证**（不能只看 patch 退出码）：

```bash
sh ./config.guess                              # 须输出 *-linux-ohos
sh ./config.sub aarch64-unknown-linux-ohos     # 须原样返回
sh ./config.sub aarch64-linux-ohos             # 须规范为 aarch64-unknown-linux-ohos
```

> 与仓内 `patch-autotools-ohos.pl` 的关系：可先跑脚本再叠加本项目补丁，二者不冲突。

### 回退方案（priority 2）— 整体替换为现代 GNU config 脚本

若该工程脚本过旧且不便逐形态打补丁，可用现代 GNU config 包**整体替换**
`config.guess`/`config.sub`（它们本就设计为"更新即用"）。代价：需在 `conandata.yml`
记录替换来源与版本，且须确认工程未对脚本做本地修改。

**仍禁止**用 `--build`/`--host` 绕过（本仓铁律，见 `patch-autotools-ohos.pl` 头部）。

### 禁止做法

- ❌ 仅凭 `set_cc_for_build` 存在就判定为"新版"并按新版插锚点——会误判并打空；
- ❌ 只看 `patch -p1` 的退出码就认为脚本可用——该形态下"插入成功"≠"运行生效"。

## 实测证据（2026-09-16，pwquality 1.4.5）

| 项 | 实测结果 |
|---|---|
| config.guess 世代 | `timestamp='2018-08-29'`；`^GUESS=`=**0**；`set_cc_for_build`=**12**；`exit ;;`=**231** |
| 仓内脚本命中率 | **Score: 1/5**（3 条 `Could not find ...` warn）|
| 补丁前 `sh ./config.guess` | `unable to guess system type` |
| 补丁前 `config.sub aarch64-unknown-linux-ohos` | 错误规范为 `aarch64-unknown-linux-gnu-ohos` |
| **补丁后 `sh ./config.guess`** | **`aarch64-unknown-linux-ohos`** ✓ |
| **补丁后 `config.sub`** | `aarch64-unknown-linux-ohos` 与 `aarch64-linux-ohos` **均**→ `aarch64-unknown-linux-ohos` ✓ |

## 测试覆盖边界

本条处理"**第三形态**（分支自行 echo）"。区分相邻情形：

- 两代格式（`GUESS=` / `set_cc_for_build`）→ `DRAFT-autotools-config-guess-two-generation-formats`；
- 脚本位于 `config/` 子目录（util-linux / lttng-ust / c-ares）→ 同族草稿已覆盖路径问题。

## 关联条目

- 相似：`DRAFT-autotools-config-guess-two-generation-formats`（二分法，本条补第三形态）
- 差异：见上方差异化定位表
