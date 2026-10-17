# DRAFT — 老 autotools 包的 config.sub 与 aarch64/musl

> 状态：草稿，待评审提升为 E 条目。配套 `.kv` 文件同名同目录。
> 来源：`archives/l/libcdaudio/0.99.12p2/`（设备实机，2026-09-14）

## 现象

照搬新包用的三元组去配置一个 2005 年的 autotools dist，configure 在第一个检查之前就死：

```text
Invalid configuration `aarch64-unknown-linux-musl':
  machine `aarch64-unknown-linux' not recognized
configure: error: ./config.sub aarch64-unknown-linux-musl failed
```

注意报错里的机器名被截成 `aarch64-unknown-linux` —— 旧 config.sub 先按
cpu-vendor-os(-os) 切分，然后把 `aarch64-unknown-linux` 当作 cpu 名去查表，查不到。

## 根因

`config.sub` 认识哪些 cpu/os 名，是随 autoconf/automake 版本演进的：

| 名字 | 加入 config.sub 的大致时间 |
|---|---|
| `musl`（os） | 约 2011 年 |
| `aarch64`（cpu） | 约 2012 年 |

竞赛池里有大量 2003–2011 年的 autotools dist，它们自带的 `config.sub` 早于这两个名字。
所以 libcaca（2018 版 config.sub）能用的 `aarch64-…-musl` / `aarch64-…-gnu` 组合，
在 libcdaudio（2005 版）上直接不可用。

## 做法

**先实测这个 dist 的 config.sub 到底认什么**，不要靠猜：

```sh
for t in aarch64-unknown-linux-gnu aarch64-linux-gnu \
         arm-unknown-linux-gnu arm-unknown-linux-musl; do
    printf '%-32s -> ' "$t"; ./config.sub "$t"
done
```

libcdaudio 2005 版 config.sub 的实测结果：

```text
aarch64-unknown-linux-gnu   -> aarch64-unknown-linux-gnu     ✅ 通过
aarch64-linux-gnu           -> Invalid configuration ...      ❌
arm-unknown-linux-gnu       -> arm-unknown-linux-gnu          ✅ 通过
arm-unknown-linux-musl      -> Invalid configuration ...      ❌（musl 不认）
```

规律：**带 `unknown` 厂商的四段名，对不认识的 cpu 是原样放行的**；三段名则会去查表。
据此构造一对"都能被接受、且彼此不同"的三元组，以保留交叉模式：

```sh
--build=arm-unknown-linux-gnu --host=aarch64-unknown-linux-gnu
```

保持 build ≠ host 很重要：交叉模式下 configure 不执行它编译出来的程序（更稳），
而且不会去跑 `config.guess`。

**前提要复核**：代码库不能按 `build_cpu` 分支。

```sh
grep -n 'case "$host"' configure.ac
```

libcdaudio 只按 `host_os` 分支 beos/irix/solaris —— 都不命中，走 generic 路径，
所以换掉 build_cpu 没有任何副作用。

## 什么时候不该用这招

- 上游 `configure.ac` 用 `$host_cpu` 做分支（少数包会）：四段名替代会让分支走错，
  这时应改为**补 config.sub / config.guess**（本仓 librevenge 就是这么做的，
  以补丁形式随配方带入现代版本）。
- 旧 config.sub 连想要的 host 名字都不认：同上，补文件。
- 包在构建期跑 autoreconf：由本机 autoconf 重新生成 config.sub（新版本认 aarch64），
  本条目无关 —— 但 OHOS 设备没有 automake/autoconf/libtoolize，这条路在本平台
  通常不可用。

## 对照：同一个三元组并不通用

| 包 | config.sub 版本 | `aarch64-*-musl` + `aarch64-*-gnu` |
|---|---|---|
| libcaca 0.99.beta20 | 2018-02-22 | ✅ 可用 |
| ncrack 0.7 | 2019 版 | ✅ 可用 |
| **libcdaudio 0.99.12p2** | **2005-04-25** | ❌ 被拒，需换四段名配对 |

这就是本条目存在的理由：不能把某个包上验证过的三元组当成通用配方。

## 顺带澄清一个常见误解

"老 autotools 包一定需要 zsh 当构建 shell"并不成立：libcdaudio 的 configure 由
**autoconf 2.59** 生成，其中 `exec 7<&0` 出现 **0 次**（libcaca 的 2.71 版有 1 次），
所以 toybox `/system/bin/sh` 的 fd 限制在这里根本不触发。真正稳定的做法是统一用
平台 profile 自己声明的 `/data/service/hnp/bin/bash`：它同时满足
"支持多位数 fd 重定向"（万一 configure 里有）和"POSIX 词分割"（automake 的
`all-recursive` 必须，zsh 不满足）。

## 验证（libcdaudio 0.99.12p2，设备实机）

```text
✅   G0: PASS
✅   G1: PASS
✅   G2: PASS
✅   G3: PASS
✅ 配方验证通过: libcdaudio 0.99.12p2
```

test_package 20/20 通过（版本上报、LBA/MSF/frame 换算、设备错误路径）。
