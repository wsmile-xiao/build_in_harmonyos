# DRAFT-lcdproc-0.5.9-config-guess-probe-before-dispatch：config.guess 里做「可选命中」的正确位置——必须放在主 dispatch **之前**

> Status: Draft | Updated: 2026-09-29
> Source: lcdproc 0.5.9 适配（`feat/lcdproc-0.5.9`）补丁 `0001-config-guess-ohos-triplet.patch`
> 对应：`knowledge/drafts/DRAFT-lcdproc-0.5.9-config-guess-probe-before-dispatch.kv`
> 关联：E007（config.guess 猜不出 HarmonyOS）、
> [DRAFT-lcdproc-0.5.9-legacy-autotools-config-anchor-miss](DRAFT-lcdproc-0.5.9-legacy-autotools-config-anchor-miss.md)

## 现象

要给 config.guess 加一条"如果编译器 target 是 ohos 就报 OHOS 三元组"的**可选**逻辑。
最自然的写法是照着 `*:HarmonyOS:*:*` 的样子，在主 dispatch 的 `case` 里也加一条
Linux 分支：

```sh
case "${UNAME_MACHINE}:${UNAME_SYSTEM}:${UNAME_RELEASE}:${UNAME_VERSION}" in
    *:HarmonyOS:*:*) ... ;;   # 真机路径
    *:Linux:*:*)
        # 想在这里做"可选命中"
        if $CC_FOR_BUILD -dumpmachine | grep -q -- '-linux-ohos'; then ... fi
        ;;
    *:Linux:*:*) ... ;;        # 原有的普通 Linux 探测
```

结果 **config.guess 对普通 Linux 机器彻底失效**：

```console
$ ./config.guess
config.guess: unable to guess system type
```

——注意它在**没有设 CC** 的普通 Linux 上也失败，而原来好好的。

## 根因

`config.guess` 的主 dispatch 是一条**互斥优先**的 `case`：一旦某个分支 pattern 命中，
shell 就**不再看后续分支**。所以往 dispatch 里塞 `*:Linux:*:*` 这种"宽 pattern"，
等于把后面所有更具体的 Linux 探测分支**全部吞掉**：

- `uname -s` 在 Linux 上恒为 `Linux`，所以 `*:Linux:*:*` 必然先命中
- 命中后走的是"可选命中"那段逻辑，若不匹配 ohos 就**直接落到 `exit`**，
  原先的 `*:Linux:*:*:*)` 正常 Linux 探测根本没机会跑
- 表现就是 `unable to guess system type`

shell `case` 没有"回溯"语义，所以这个坑**不能靠分支顺序救**——
`*:Linux:*:*` 无论放前放后都会吃掉一类探测。

## 正解

把"可选命中"提到主 dispatch **之前**的独立 `case` 里，命中就 `exit`，
不命中就自然落回原来的 dispatch：

```sh
# ---- 放在主 dispatch 之前 ----
ohos_target=`$CC_FOR_BUILD -dumpmachine 2>/dev/null`
case "$ohos_target" in
*-linux-ohos)
    ohos_mach=`echo "$ohos_target" | sed 's/-.*//'`
    echo "${ohos_mach}-unknown-linux-ohos"
    exit ;;
esac

# ---- 然后才是原来的主 dispatch ----
case "${UNAME_MACHINE}:${UNAME_SYSTEM}:${UNAME_RELEASE}:${UNAME_VERSION}" in
    *:HarmonyOS:*:*) ... ;;   # 真机 uname 路径
    *:NetBSD:*:*)   ... ;;
    *:Linux:*:*:*)  ... ;;    # 原有普通 Linux 探测，未被破坏
```

### 关于 `$CC_FOR_BUILD`

2014-03-23 版 config.guess 里有：

```sh
CC_FOR_BUILD=${CC_FOR_BUILD-"$CC"}
```

即**它会自动采纳环境里的 `CC`**。所以探针直接用 `$CC_FOR_BUILD` 就行，
不必自己 `which clang`、也不必解析 `cc`/`gcc` 软链。`CC` 没设时
`$CC_FOR_BUILD` 为空、`-dumpmachine` 静默失败（`2>/dev/null`）、
`case` 全部不匹配、直接落回原 dispatch —— 这正是想要的"可选"语义。

## 为什么必须"两条路"都有

| 场景 | 命中哪条 | 靠什么探测 |
|---|---|---|
| 真机 OHOS CI worker（`uname -s` = `HarmonyOS`） | dispatch 内的 `*:HarmonyOS:*:*` | uname |
| 交叉构建（普通 Linux 机器 + OHOS 工具链） | dispatch **之前**的 target 探针 | `$CC_FOR_BUILD -dumpmachine` |

两条都留，本地交叉构建与真机 CI 才能得到**同一个** host：

```console
$ ./config.guess                                   # 无 CC，普通 Linux 探测未被破坏
x86_64-unknown-linux-gnu
$ CC=/opt/lpk-fixed/clang ./config.guess
aarch64-unknown-linux-ohos
$ ./configure
checking host system type... aarch64-unknown-linux-ohos
checking whether we are cross compiling... no        # 关键：仍是 no
```

最后那行 `cross compiling... no` 是重点。E007 forbid_1 禁的是
`--build=`/`--host=`，而这套探针走的是"让 config.guess 自己猜对"，
所以不触发交叉编译判定，`AC_RUN_IFELSE` 一个都不会被跳过。

## 验证

```sh
./config.guess                                   # 期望 <build-machine>-unknown-linux-gnu
CC=<ohos-clang> ./config.guess                   # 期望 aarch64-unknown-linux-ohos
CC=<ohos-clang> ./configure 2>&1 | grep -E 'host system type|cross compiling'
```

三条全过才算修好。**只测第二条不够**——第一版补丁就是只过了第二条，
而第一条（普通 Linux 探测未被破坏）是被吞掉的那类。
