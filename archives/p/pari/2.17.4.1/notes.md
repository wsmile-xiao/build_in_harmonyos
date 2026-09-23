# pari 2.17.4 — 鸿蒙 PC conan 包（GMP 内核 + 线程局部栈）

## 为什么是 2.17.4，为什么必须是 GMP + TLS

目标下游是 **passagemath-pari**（进而 `sage.libs.pari`、GF(2^e) 有限域、p-adic 等）。
上游 `passagemath_pari-10.8.7-cp311-cp311-musllinux_1_2_aarch64.whl` 里打包的是：

```
passagemath_pari.libs/libpari-gmp-tls-37c151a6.so.2.17.4
  DT_NEEDED  libgmp.so.10
  GP/PARI CALCULATOR Version 2.17.4
```

库名不是随便起的——PARI 的 `Configure` 按内核拼出来：

```
Configure:104   gmp)  libpari_base=pari-gmp
Configure:108   yes)  libpari_base="${libpari_base}-tls"
```

所以 `--with-gmp` 与 `--enable-tls` **同时决定 soname**，不是可选的性能开关。
下游 cypari2 按这个名字加载。

> 本仓已有一份 `archives/p/pari/2.17.3`（cmd-pkgs 形态，2026-06-04）是
> 「内置大数替代 GMP」编的，产物是 `libpari.so`——**库名就对不上**，
> passagemath-pari 用不了。两者并存、互不冲突。

## 五轮踩坑（都写在 recipe 注释里，避免重走）

### 1. `pthread_cancel` / `pthread_setcanceltype` 不存在 → 去掉 `--mt=pthread`

```
ld.lld: error: undefined symbol: pthread_setcanceltype
>>> referenced by pthread.c → pthread.o:(mt_sigint_block)
```

**先证伪再动手**：`readelf -sW` 查这套 libc，确认
`pthread_cancel`/`pthread_setcanceltype` **确实没有**、而 `pthread_create` **有**——
所以不是「没链上」，是真不存在，去掉该引擎是唯一解。

`--mt=pthread` 只是 PARI **自带的并行计算引擎**，
去掉它 **不影响 soname**（库名只由 gmp+tls 决定），cypari2 也不使用该引擎。
⚠️ 别顺手把 `--enable-tls` 一起关掉——那会让库名变成 `libpari-gmp`，下游直接链不上。

### 2. 只产出 `libpari.a`，没有共享库 —— 表象，真因在下一条

### 3. 【真根因】`config/arch-osname` 不认 HarmonyOS → `arch=none` → 全面退化

构建目录出现 `Oharmonyos-none` 是最早的可见信号：

```sh
# config/arch-osname:3
myuname=`(uname -a) 2>/dev/null || arch 2>&1`
set X $myuname; shift; osname=$1        # 取 `uname -a` 的**第一个词**
case "$osname" in
  irix*) ... linux) ... darwin*) ...    # 无 harmonyos 分支
```

设备 `uname` 报 HarmonyOS → 无分支命中 → `arch` 保持文件开头的初值 `none`
→ 构建目录 `O<osname>-none`、**不产共享库**、汇编内核退成通用 C 实现。

**`patches/0001` 给它加 `harmonyos*|ohos*` 分支**，按 linux 处理并取 `uname -m`；
`config/get_kernel:44,57` 认 aarch64，随即正常产出 `libpari-gmp-tls.so` 并选对内核。

> ❌ **uname 垫片不管用，别再试**：靠 PATH 前缀塞一个假 uname，会被
> `self.run(env="conanbuild")` 的环境脚本重设 PATH 盖掉——实撞一轮，
> 判据显示构建目录仍是 `Oharmonyos-none`。改源码才是确定性的。
>
> 另：垫片若真要用，**必须连 `uname -a` 一起管**——PARI 读的正是 `-a`，
> 只处理 `-s`/`-m` 等于没垫。

### 4. 【易错】链接名是 `pari`，不是 `pari-gmp-tls`

装出来是三个文件：

```
libpari-gmp-tls.so.2.17.4      实体
libpari-gmp-tls.so.9  → 实体   SONAME 指向它
libpari.so            → 实体   **未加版本号的链接名只有这一个**
```

`cpp_info.libs` 写 `pari-gmp-tls` 会得到
`Library 'pari-gmp-tls' not found in package`（实撞一轮）。
**链接用 `-lpari`，运行期由 SONAME 加载 `libpari-gmp-tls.so.9`**——两者是不同的东西。
上游 cypari2 同样是 `-lpari`。

### 5. 【CI 实撞】`LD` 被设成裸链接器 → 找不到 `-lm`

```
ld.lld: error: unable to find library -lm
make: *** [Makefile:1147: gp-dyn] Error 1
```

PARI **用 `$LD` 直接链可执行文件**（`config/get_ld`：只有 `LD` 为空时才回落到 `$CC`）。
CI 环境里 `LD=ld.lld`，链接命令就绕过了编译器驱动 —— 裸链接器没有 sysroot、
没有默认库搜索路径，于是找不到 `libm.a`（它明明就在 SDK sysroot 里）。

对照两边的链接命令，一眼可辨：

```
本机   /data/service/hnp/bin/clang  -o gp-dyn ... -lm      ← 走驱动，OK
CI     ld.lld  -o gp-dyn ... -lm                            ← 裸链接器，失败
```

> ⚠️ **本机通过不代表可移植**：本机只是恰好没设 `LD`。
> 这类「同一份 recipe 本机过、CI 挂」的差异，要去比**实际执行的命令**，
> 而不是猜平台缺什么库——我最初以为是 musl 没有独立 libm，方向就错了。

修法：configure 参数里显式 `LD=<C 编译器>`，不受环境影响；
这也正是 PARI 自己的默认意图。

### 6. `package()` 不用 `make install`

`config/Makefile.SH:370` 的 `install:` 含 `install-doc`，那步要 TeX 生成 dvi；
conan 包也不需要文档。改用 `make install-nodata` + `make install-data`。
后者会装 `share/pari/pari.desc`——**cypari2 构建时要读它**，不能省。

## 质量状态

真机（HarmonyOS PC MateBook）用 CI 的 profile `conan create` 通过。

```
构建目录     Olinux-aarch64                       （不再是 O*-none）
产物         libpari-gmp-tls.so.2.17.4  10.7 MB
SONAME       libpari-gmp-tls.so.9
DT_NEEDED    libc.so, libgmp.so.10                （确为 GMP 内核）
版本         GP/PARI CALCULATOR Version 2.17.4 (released)
数据         share/pari/pari.desc                 （cypari2 依赖）
```

`test_package` **校验计算结果**而非只看能否链接：

```
stoi/itos 往返 1234
2^64 = 18446744073709551616        （十进制 20 位）
nextprime(1000) = 1009
→ pari test_package: 全部断言通过
```

## 已知取舍

- **开 readline**（`readline/8.3`）：下游 passagemath-pari 的 **PARIKernel**
  需要它的头文件，缺了直接
  `PARIKernel/kernel.c:1166:10: fatal error: 'readline/readline.h' file not found`。

  > 此处**曾判断错一次**：最初按「库本身不需要 readline」关掉它，理由是
  > gp 的交互补全与 Python 绑定无关。但上游 wheel 打包了 `libreadline` /
  > `libncursesw`，说明上游就是开着编的；判断该以**下游实际需要**为准，
  > 而不是「这个库自己用不用得上」。同一类误判在本包出现过三次
  > （gp 不在 PATH、gp 未签名跑不了、gphelp 被 install-doc 一起砍掉），
  > 根子都是把它当纯 C 库打包，而下游要的是**一套能运行的 PARI 安装**。
- **不开 `--mt=pthread`**：见坑 1，平台 libc 缺必需符号。
  PARI 的并行计算引擎不可用；cypari2 / passagemath-pari 不使用它。
