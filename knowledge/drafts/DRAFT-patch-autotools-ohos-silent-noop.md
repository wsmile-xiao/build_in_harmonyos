# DRAFT-patch-autotools-ohos-silent-noop — `patch-autotools-ohos.pl` 对 2014/2015 版 autotools 的静默失效

> 配对的 kv：`knowledge/drafts/DRAFT-patch-autotools-ohos-silent-noop.kv`
> 来源：pcc（Portable C Compiler）1.2.0-devel-20220331 适配，PR !14348
> 分类：autotools / tooling

## 错误特征

脚本**退出码 0**，但补丁完全没生效；`configure` 仍报：

```
sh ./config.guess        →  rc=1，报 unable to guess system type
sh ./config.sub aarch64-unknown-linux-ohos
                         →  报 machine 'aarch64-unknown-linux' not recognized
```

## 根因分析

官方 `scripts/patch-autotools-ohos.pl` 是按**新版** autotools 的 `config.guess`
结构编写的：

- 新版的系统识别块**只负责赋值** `GUESS`，由外层统一 `echo` + `exit`；
- **2014/2015 版**的 `config.guess` 里，**每个 case 分支必须自己 `echo` 三元组并 `exit`**
  （文件末尾是一个「unable to guess system type」的错误块）。

于是脚本把「只赋值 `GUESS`」的块插进老文件后，控制流在该分支既不输出也不退出，
**继续落到文件末尾的错误块**。同时 `config.sub` 的锚点（`android-linux`、
`linux-uclibc` 等）在老文件中也不存在。

结果：**三处修改全部不命中，脚本 exit 0、看起来成功，实际一个改动都没落地。**
pcc 实测只命中 **1/5**（这正是它为什么必须手工改写）。

## 推荐方案

**方法**: `manual-minimal-rewrite-in-file-style`

1. **不要信任该脚本的退出码**；
2. 用**实际输出**判定，而不是退出码：

   ```sh
   sh ./config.guess                              # 期望 echo 出 aarch64-unknown-linux-ohos
   sh ./config.sub aarch64-unknown-linux-ohos     # 期望原样接受
   ```

3. 失败则按**目标文件自身的分支风格**手工最小改写。

pcc 的手工改写（补丁 0001）——注意老版必须自带 `echo` + `exit`：

```sh
    *:HarmonyOS:*:*)
        case "$UNAME_MACHINE" in
            aarch64|arm64) MACHINE=aarch64 ;;
            armv7*|armv8*) MACHINE=arm ;;
            x86_64|amd64)  MACHINE=x86_64 ;;
            i?86)          MACHINE=i686 ;;
            *)             MACHINE="$UNAME_MACHINE" ;;
        esac
        echo ${MACHINE}-unknown-linux-ohos
        exit ;;
```

## 陷阱

**禁止**只依据 `patch-autotools-ohos.pl` 的退出码判定补丁成功 ——
对老版 autotools 文件它会 exit 0 但完全未改写，导致白排一轮错。

```sh
# 反向核验（命中即说明脚本没生效，仍在走错误块）
grep -n 'unable to guess system type' config.guess
```

## 与现有知识库的关系

这是对 **E007**（「用 `patch-autotools-ohos.pl` 一键打补丁」）的**静默失效修正**：
E007 的推荐方案对本条覆盖的这一类项目（config.guess 为 2014-11-04 及更早版本、
config.sub 分支风格与新版不同）会 exit 0 但零改写，必须改用「实际输出判定 + 手工最小改写」。
