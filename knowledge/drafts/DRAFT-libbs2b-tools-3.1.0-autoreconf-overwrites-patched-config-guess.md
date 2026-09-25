# DRAFT: autoreconf -fi 会把 tarball 的 config.guess/config.sub 换成 automake 的副本

> Contributor: username- | Status: DRAFT | Created: 2026-09-17
> 来源: libbs2b-tools 3.1.0 适配（libbs2b 的库 + bs2bstream + bs2bconvert 同工程）

## 症状

tools 包要在 `configure.ac` / `src/Makefile.am` 上打补丁（把 sndfile 变成可选、
给两个 CLI 补 `--version`/`--help`），因此必须重新生成 `configure` / `Makefile.in`：

```
autoreconf -fi
./configure --host=aarch64-unknown-linux-ohos ...
```

`autoreconf` 一路成功，补丁也没有一条冲突，但 `configure` 紧接着报：

```
configure: error: cannot guess build type; you must specify one
```

## 根因

两件事叠在一起：

1. **补丁面在 `.ac`/`.am` 上就必须 autoreconf**，没有别的选择；
2. **autoreconf 的 automake 环节会 `--add-missing`**，把 `config.guess`、`config.sub`、
   `install-sh`、`compile`、`depcomp`、`missing` 按 **automake 自己的副本**重装到
   `AC_CONFIG_AUX_DIR` 下。

于是对 tarball 里老 `config.guess` 打的 HarmonyOS 补丁，生效窗口只有 autoreconf 之前
那一小段——补丁干净地应用了，然后被 automake 的副本整个覆盖掉。

更坑的是**新换上的副本也不认 HarmonyOS**。用假 `uname` 模拟鸿蒙机器，三份副本的表现：

| config.guess | `uname -s` = HarmonyOS, `-m` = aarch64 时的输出 |
|---|---|
| tarball 自带的 2009-06-05 副本（45630B） | 只打印 `UNAME_SYSTEM = "HarmonyOS"` 诊断，退出 1 |
| automake 1.18 的副本（50743B） | 同样只打印 `UNAME_*` 诊断，退出 1 |
| 配方携带的补丁后副本（51014B） | `aarch64-unknown-linux-ohos` |

也就是说 `config.sub` 认 `aarch64-unknown-linux-ohos` 并不代表 `config.guess` 猜得出来——
前者是字符串校验，后者要真的把 `uname -s = HarmonyOS` 映射过去。

## 判据（不必占鸿蒙设备）

```sh
mkdir -p /tmp/fb
printf '#!/bin/sh\ncase "$1" in -s) echo HarmonyOS;; -m|-p) echo aarch64;; -r) echo kr;; -v) echo v;; *) echo x;; esac\n' > /tmp/fb/uname
chmod +x /tmp/fb/uname
env -i PATH=/tmp/fb:/usr/bin:/bin HOME=/tmp ./config.guess
# 期望 aarch64-unknown-linux-ohos，打印 UNAME_SYSTEM = HarmonyOS 就是猜不出来
```

再看一眼 autoreconf 到底动没动这两个文件：

```sh
sha256sum build-aux/config.guess build-aux/config.sub   # autoreconf 前后各跑一次
```

## 修复

不要把补丁打在 tarball 的老副本上，改成"覆盖之后写回"：

1. 补丁后的成品副本随配方携带（`export_sources()` 导出 `support/`）；
2. `autoreconf -fi` 之后、`configure` 之前，把 `support/config.guess`、
   `support/config.sub` 覆盖到 `AC_CONFIG_AUX_DIR`；
3. 覆盖动作要容忍 `export_sources_folder == source_folder`——Conan 2.30 把导出源码
   直接铺进源码树，此时 `copy(src, dst)` 的 `src` 与 `dst` 是同一个目录，
   会抛 `copy() 'src' and 'dst' arguments must have different values`（老版本 Conan 不会）。

## 同一次适配里另外两个必踩的点

- **worker 上没有 automake。** `/data/service/hnp` 下只有 autoconf 家族，
  `autoreconf -fi` 直接死在
  `Can't exec "aclocal": No such file or directory at .../autoconf/Autom4te/FileUtils.pm`。
  解法是 `build_requirements()` 里 `tool_requires("automake/1.18")` +
  `tool_requires("libtool/2.5.4")`，再用 `VirtualBuildEnv(self).generate()` 把它们塞进
  `conanbuild` 环境。aclocal 找 `pkg.m4` 等宏还要显式给路径：
  `ACLOCAL_PATH` 追加 `/data/service/hnp/*/*/share/aclocal`。
- **`autoconf -fi` 重新生成的 `configure` 里 `umask 077 && mktemp -d` 在 HMDFS 上不可写。**
  HMDFS 忽略 chmod，`umask 077` 建的临时目录随后写不进去，`config.status` 报
  `can't create ./confXXXXXX/subs1.awk: Permission denied`。按行匹配片段很脆
  （autoconf 各版本写法不同），直接全文把 `umask 077` 换成 `umask 000` 更稳。

## 补记（2026-09-19）：为什么"整份携带现代 config.guess/config.sub"是错的路

第一版实现是：把一份认识 `aarch64-unknown-linux-ohos` 的现代 `config.guess`（1823 行）
与 `config.sub`（1966 行）随配方携带（`support/`），`autoreconf -fi` 之后盖回
`build-aux/`。功能上没问题，但**代价在平台的自动审查上**：

```
🤖 AI Code Review
⚠️ 本次变更过大（8 个可审文件、4172 行，预估需 N 轮分片审查），
   已超出 AI 代码评审的处理范围，本次跳过。
```

于是 rule6（"必须有有效 AI 检视且 P0/P1=0"）**直接不通过**，而且这个失败没有对应的
具体缺陷可修 —— 它惩罚的是"补丁体积"，不是代码质量。

### 正确做法：只注入缺的分支

`autoreconf` 之后对刚生成的 `build-aux/config.guess` / `config.sub` 做**最小改写**：

1. 优先调用仓库自带脚本 `scripts/patch-autotools-ohos.pl`
   （E007 的官方打法：注入 `__OHOS__ → LIBC=ohos` 与 `*:HarmonyOS:*:*` 分支）；
2. 脚本不可用或锚点不存在时，退回内置最小改写（幂等）：
   - `config.guess`：在 `*:NetBSD:*:*` 前插入 `*:HarmonyOS:*:*` 分支，
     输出 `${MACHINE}-unknown-linux-ohos`；
   - `config.sub`：把 `ohos*` 加进 OS 白名单、`linux-ohos*` 加进内核-OS 校验、
     并让 `-linux-ohos` 不被归一化成 `-linux-gnu`（远古版本还需补 `aarch64`/`arm64` 的 CPU 规则）；
3. 注入后**静态自检**两份脚本都出现 `HarmonyOS`/`ohos` 标记，否则立刻报错，
   不要留给 `configure` 用 `cannot guess build type` 收场。

实测（现代 automake/libtool 产物）：注入后 `sh config.guess` 输出
`aarch64-unknown-linux-ohos`，`sh config.sub aarch64-unknown-linux-ohos` 原样回显；
PR diff 从 **4757 行降到约 1000 行**，可审文件从 8 个（含两个 1800+ 行辅助脚本）
降到 7 个、总量约 650 行。

> 一句话：**当"能跑"与"能被审"冲突时，选体积最小的那个实现** ——
> 自动审查对 diff 体积有硬上限，整份替换辅助脚本会把 PR 推到上限之外。

## 勘误（2026-09-20，来自 AI 检视的一条有效意见）

原 `rec_command` 写成：

```sh
autoreconf -fi && cp support/config.guess support/config.sub $(dirname $(grep -m1 AC_CONFIG_AUX_DIR configure.ac))
```

**这条命令是错的**：`grep -m1 AC_CONFIG_AUX_DIR configure.ac` 输出的是**整行**
`AC_CONFIG_AUX_DIR([build-aux])`，整行里没有 `/`，POSIX `dirname` 对它返回 `.`；
于是 `cp` 把两个辅助脚本复制到**源码树根目录**（目标是已存在的目录，`cp` 返回 0，**静默成功**），
而 `build-aux/config.guess` 仍是 automake `--add-missing` 装上的那一份 —— `configure` 继续报
`cannot guess build type`，使用者却以为"已经按知识库写回过了"。

正确写法（并给命令替换加引号）：

```sh
auxdir=build-aux   # 直接取 AC_CONFIG_AUX_DIR([build-aux]) 的值，不要在整行上做 dirname
perl "$OHC_SKILL_ROOT/scripts/patch-autotools-ohos.pl" "$auxdir/config.guess" "$auxdir/config.sub"
grep -c HarmonyOS "$auxdir/config.guess"   # 静态自检，必须非 0
```

> 顺带一条更通用的教训：**知识条目里的"可复制命令"必须真跑一遍**。
> "对 `grep` 出来的整行做 `dirname`"这类错误不会报错（`cp` 静默成功），
> 却让使用者在同一条坑里再摔一次。
