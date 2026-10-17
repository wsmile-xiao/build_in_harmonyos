# DRAFT-lcdproc-0.5.9-legacy-autotools-config-anchor-miss：2014 年代 config.guess/config.sub 的两个失效

> Status: Draft | Updated: 2026-09-29
> Source: lcdproc 0.5.9 适配（`feat/lcdproc-0.5.9`）补丁 `0001-config-guess-ohos-triplet.patch` / `0002-config-sub-linux-ohos.patch`
> 对应：`knowledge/drafts/DRAFT-lcdproc-0.5.9-legacy-autotools-config-anchor-miss.kv`
> 关联：[E007](../../graph/E007.kv)、[E072](../../graph/E072.kv)、
> [DRAFT-lcdproc-0.5.9-config-guess-probe-before-dispatch](DRAFT-lcdproc-0.5.9-config-guess-probe-before-dispatch.md)

这是 E007 / E072 在**老 vintage** 脚本上的变体。E007/E072 的签名在老脚本上
**根本不出现**——因为你在撞上"补丁脚本没打上"之前就已经卡住了。

## 失效 (1)：官方补丁脚本的锚点全失配

`scripts/patch-autotools-ohos.pl` 的所有锚点都取自 2015 年之后的
config.guess / config.sub 形态：

| 锚点 | 2014-03-23 config.guess / 2014-09-11 config.sub |
|---|---|
| `__ANDROID__` 宏 | 不存在 |
| `android-linux` 分支 | 不存在 |
| `linux-uclibc` kernel-OS 条目 | 不存在 |

lcdproc 0.5.9 的 tarball 自带的正是这两个 vintage，于是脚本**一个锚点都匹配不上**：

```console
$ perl scripts/patch-autotools-ohos.pl config.guess config.sub
...
Score: 1/5
```

`Score: 1/5` 是信号：**必须自己写补丁**。更要命的是脚本在这种状态下仍然
report success——"什么都没打上"被当成了成功。如果不盯着 `Score` 字段，
你会以为打好了，然后一头撞进 `unable to guess system type`。

**判 vintage 的一行命令**：

```sh
grep -c '__ANDROID__\|android-linux' config.guess config.sub   # 两个 0 = 2015 前
head -20 config.sub | grep '20[12][0-9]'                        # 看版权年份
```

## 失效 (2)：config.sub 在 2014 版上是**两处**不是三处

E072 说 config.sub 要改三处：

1. `ohos-linux` → `basic_os=linux-ohos` 的映射分支
2. `case $os` 的 OS 白名单加 `ohos*`
3. `case $maybe_os` 的 kernel-OS 白名单加 `linux-ohos*`

**2014 版只有 2 和 3。** 第 1 处（`basic_os` 映射分支）在这个 vintage 里
**根本不存在**——老 config.sub 的 OS 归一化不靠 vendor 映射分支，
靠的是末尾 `case $os` 的 vendor 白名单。于是照 E072 去找那三处的人会
在第 1 处卡住，或者更糟：找到一个形似的分支改了，结果没用。

实际要改的两处（用**模式**定位，别用行号，vintage 之间行号会漂）：

```diff
--- a/config.sub
+++ b/config.sub
@@ -115,7 +115,8 @@
  # Here we must recognize all the valid KERNEL-OS combinations.
  maybe_os=`echo $1 | sed 's/^\(.*\)-\([^-]*-[^-]*\)$/\2/'`
  case $maybe_os in
-  nto-qnx* | linux-gnu* | linux-android* | linux-dietlibc | linux-newlib* | \
+  nto-qnx* | linux-gnu* | linux-android* | linux-ohos* | linux-dietlibc | \
+  linux-newlib* | \
    linux-musl* | linux-uclibc* | uclinux-uclibc* | uclinux-gnu* | kfreebsd*-gnu* | \

@@ -1376,7 +1377,7 @@
  	      | -cegcc* \
  	      | -cygwin* | -msys* | -pe* | -psos* | -moss* | -proelf* | -rtems* \
-	      | -mingw32* | -mingw64* | -linux-gnu* | -linux-android* \
+	      | -mingw32* | -mingw64* | -linux-gnu* | -linux-android* | -linux-ohos* \
  	      | -linux-newlib* | -linux-musl* | -linux-uclibc* \
```

## 最坑的一点：只改 kernel-OS **不报错**，但结果是错的

**只改第 1 处**（kernel-OS 白名单）时，config.sub **不会报任何错**，
但它会把三元组规范化成：

```
aarch64-unknown-linux-ohos   ->   aarch64-unknown-linux-gnu-ohos
```

一个**看起来合法、实则错误**的 vendor。`gnu` 会被后面所有路径当成普通 glibc
Linux 平台对待，错误一路带到链接期和运行期，且**离根因非常远**。
只改末尾那处（OS 白名单）则连 kernel-OS 校验都过不去，会明确报
`Kernel 'linux' not known to work with OS 'ohos'`。

**两处都要改。**

## 验证必须双向

单向验证（"OHOS 三元组能过"）不足以说明没把老三元组打坏：

```sh
./config.sub aarch64-unknown-linux-ohos     # 期望原样输出，绝不能变成 -gnu-ohos
./config.sub x86_64-linux-gnu               # 期望行为不变
./config.sub aarch64-unknown-linux-gnu-ohos # 应当报错（确认白名单真的收紧了）
```

实测（lcdproc 0.5.9，打完补丁后）：

```console
$ ./config.sub aarch64-unknown-linux-ohos
aarch64-unknown-linux-ohos
$ ./config.sub x86_64-linux-gnu
x86_64-pc-linux-gnu
```

## 别忘了 config.guess 那一半

config.sub 改对了还不够——config.guess 得先**猜出** `aarch64-unknown-linux-ohos`
才能轮到 config.sub 验证。而且 config.guess 的改动有个独立的坑：
"可选命中"的探针必须放在主 dispatch **之前**，
详见 [DRAFT-lcdproc-0.5.9-config-guess-probe-before-dispatch](DRAFT-lcdproc-0.5.9-config-guess-probe-before-dispatch.md)。
