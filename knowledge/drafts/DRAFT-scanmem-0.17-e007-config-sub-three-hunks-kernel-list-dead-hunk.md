# DRAFT-scanmem-0.17: E007 的 `config.sub` 要补三处，且框架脚本第三处是死代码

## 症状

scanmem 0.17 的 GitHub tag 归档**不带**预生成的 `configure`（release 资产 404），
所以必须 `autoreconf -fi` 引导。引导之后 configure 连第一阶段都过不去：

```
configure: error: /bin/bash ./config.sub aarch64-linux-ohos failed
configure: error: Invalid configuration `aarch64-linux-ohos': OS `ohos' not recognized
```

按框架 `scripts/patch-autotools-ohos.pl` 打上补丁后（它报告 `Score: 4/5`、`ohos*=1`、
看起来成功），**仍然失败，只是换了副面孔**：

```
configure: error: Invalid configuration `aarch64-linux-ohos': Kernel `linux' not known to work with OS `ohos'.
```

## 根因

`config.sub` 里 ohos 需要改**三张互相独立的表**，脚本只改到了两张：

| 表 | 作用 | 不改的后果 |
|---|---|---|
| CPU-VENDOR-OS 三元组分支 | `<x>-linux-ohos` → `basic_os=linux-ohos` | triplet 被拒 |
| `case $os in` OS 类型表 | 承认 `ohos` 是一个合法 OS | `OS 'ohos' not recognized` |
| `case $kernel-$os in` 校验表 | 承认 `linux` 内核可配 `ohos` OS | `Kernel 'linux' not known to work with OS 'ohos'` |

第三处是**死代码**，不是环境差异：

```perl
# 2.3 kernel-OS hunk
unless ($sc =~ /linux-ohos/) { ...add linux-ohos to kernel list... }
# 而 2.1 刚刚写入了：  basic_os=linux-ohos
```

2.1 一旦成功，全局 `/linux-ohos/` 必然命中，2.3 直接跳过。所以「脚本跑完
`Score: 4/5`」并不代表 kernel 表被改了——4/5 里那一项正是被短路的。
（lftp/4.9.3 的 notes 已记录过这个现象，本次在另一个包上独立复现。）

## 第二层坑：自己写补丁时把 config.sub 改成语法错误

复刻 2.1 时用「分别捕获缩进分组再重建 case 分支」：

```python
m = re.search(r"...basic_os=linux-android[ \t]*\n([ \t]*;;[ \t]*\n)", cs)
```

`basic_os=linux-android` 之后的**尾部** `[ \t]*` 把下一行 `;;` 的缩进一起吃掉了，
重建结果多出一个零缩进的裸 `;;`，`config.sub` 变成 shell 语法错误。而 configure
对此只报一句：

```
configure: error: cannot run /bin/bash ./config.sub
```

——看起来像「缺 shell」，实际是补丁写坏了脚本，排查方向会被带偏很远。

## 第三层坑：`env -u CONFIG_SHELL` 会掉进另一个坑

为规避 hnp bash 在 HMDFS 上 `getcwd()` 失败（gtypist/2.10.1 §12.38①），
常见写法是 `env -u CONFIG_SHELL SHELL=/bin/sh`。在本项目里这会引入新问题：
autoconf 在 `CONFIG_SHELL` 为空时**回落到硬编码的 `/bin/bash`** 去跑
`config.sub`，而 OHOS worker 上没有 `/bin/bash`：

```
configure: error: cannot run /bin/bash ./config.sub
```

正解是**显式设** `CONFIG_SHELL=<健康 shell>`，一处同时解决两个问题。

## 最终方案

1. `autoreconf -fi` **之后**再打 E007 补丁——autoreconf 会重装
   `config.guess`/`config.sub`，先打补丁会被无声覆盖。
2. `config.sub` 三处全改，kernel 表的守卫条件针对 **kernel 列表本身**
   （`linux-uclibc* | linux-ohos*`），而不是全局 `/linux-ohos/` 搜索。
3. 三元组分支用**整体克隆 `android-linux` 分支 + 字符串替换**生成
   （`replace("android-linux)", "ohos-linux)")` + `replace("basic_os=linux-android", "basic_os=linux-ohos")`），
   缩进天然一致，语法错误不可能发生。
4. 补丁落盘后立刻 `sh -n config.sub` 自检，失败就抛异常，让问题在打补丁
   当场暴露，而不是等 configure 报一句指向错误位置的 `cannot run`。
5. `CONFIG_SHELL` / `SHELL` 都显式设为 `/system/bin/sh`（或 `/bin/sh`）。

## 适用边界

- **适用**：任何需要 `autoreconf` 引导的 autotools 项目（tag/git 归档、
  仓库里没有 release tarball 的项目）在 OHOS 上构建。
- **注意**：若构建机的 autotools 足够新（config.sub 已原生认识 ohos），
  三处补丁都应命中「已存在」分支而空操作；配方必须**幂等**，
  不能假设补丁一定需要打。
- **不适用**：tarball 自带预生成 `configure` 的项目——那类项目仍需补
  `config.guess`/`config.sub`（lftp/4.9.3 正例），但不需要 autoreconf 引导，
  补丁位置也不同（`build-aux/` 而非源码根）。
