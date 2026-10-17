# 草稿：老版 config.guess HarmonyOS 分支的两个坑（模式失配 + 未输出）

> 与正式条目 **E007**（config.guess 无法识别 HarmonyOS）配套，建议合并进 E007 的注意事项。

## 现象

```
configure: error: cannot guess build type; you must specify one
config.guess: unable to guess system type
  UNAME_MACHINE = aarch64
  UNAME_SYSTEM  = HarmonyOS
  UNAME_VERSION = #1 SMP Wed Apr 29 10:16:03 UTC 2026
```

## 坑 1：`*:HarmonyOS:*:*` 模式失配

`config.guess` 的 case 字符串是 `"${UNAME_MACHINE}:${UNAME_SYSTEM}:${UNAME_RELEASE}:${UNAME_VERSION}"`。
OHOS 的 `uname -v` 含冒号（`10:16:03`），字段数 > 4，四段模式（`*:*:*:*`）匹配失败。
→ 用三段模式 `*:HarmonyOS:*)`。

## 坑 2：老版脚本要求 `echo` + `exit`

2006/2008 版 config.guess 的每个分支都是 `echo <triplet>; exit 0`（没有统一的尾部 echo）。
补丁若只写 `GUESS=...`，脚本会继续执行兜底分支（尝试 `$CC_FOR_BUILD` 编译探测）并最终
`cat >&2 <<EOF ... unable to guess system type` + `exit 1`。
→ 分支体必须是 `echo ${MACHINE}-unknown-linux-ohos; exit 0`。

## 坑 3：config.sub 需同步补四处

| 位置 | 补入 |
|------|------|
| maybe_os 列表 | `linux-ohos*` |
| CPU 列表 | `aarch64` |
| cpu-company 列表 | `aarch64-*` |
| os 分支（`-linux-dietlibc)` 前） | `-linux-ohos) os=-linux-ohos ;;` |

漏掉任一处，`configure` 会报 `Invalid configuration 'aarch64-linux-ohos': machine 'aarch64-linux' not recognized`。

## 验证

```bash
./config.guess                              # → aarch64-unknown-linux-ohos
./config.sub aarch64-unknown-linux-ohos     # → aarch64-unknown-linux-ohos
```

## 来源

maq/0.7.1（config.guess timestamp = 2006-07-02）适配实测。
