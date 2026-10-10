# pcc 1.2.0-devel-20220331 — 适配笔记

平台：HarmonyOS PC（aarch64，musl libc），工具链 /data/service/hnp/bin/clang (clang 15.0.4)，
conan 2.29.1，profile `ci/conan/profiles/ohos-aarch64`（-pr:h 与 -pr:b 同一份）。

## 一、任务定位（最关键的一点）

**pcc 没有 aarch64 代码生成后端。**

`arch/` 下的后端是：amd64、arm(32 位)、hppa、i386、i86、m16c、m68k、mips、
mips64、nova、pdp10、pdp11、pdp7、powerpc、sparc64、vax。
其中 `arm` 是 **ARMv7（32 位）**，不是 aarch64。

`configure.ac` 对目标 CPU 的映射是一串 `case "$target_cpu"`；`aarch64` 不匹配其中
任何一支（`arm*` 通配的是 `arm` 前缀），于是 `targmach` 为空，紧接的第 289-291 行直接：

```
if test "X$targos" = X -o "X$targmach" = X ; then
	AC_MSG_ERROR(['$target' is not (yet) supported by pcc.])
fi
```

因此本任务的正确形态是：**把 pcc 编译器本体移植到鸿蒙 PC 上运行**，而不是让它
生成鸿蒙 aarch64 代码。这一点与官方已合入的编译器类案例一致：

| 案例 | 形态 |
|---|---|
| chibicc 1.0.24.1 | 在 OHOS/armv8 上运行，生成 x86-64 代码 |
| asmc-linux 2.39 | ARM64 原生 host 汇编器，输出 x86/x86-64 ELF |
| 本包 pcc | 在 OHOS/aarch64 上运行，默认目标三元组 amd64-linux |

## 二、为什么传 `--target` 而不传 `--host`

仓库口径是「native 编译禁用 `--build=`/`--host=`/`--target=`，一律改
config.guess/config.sub」。本包的处理是**只保留 `--target=amd64-linux`，不传
`--host`**，理由如下（均为本机实测，非推断）：

1. **`--target` 不是平台探测绕过，而是产品定义。** pcc 是可变目标编译器，必须被告知
   生成哪套后端；`arch/` 里没有 aarch64，若 target 缺省成 host 就会撞上上面那段
   `AC_MSG_ERROR`。config.guess/config.sub 描述的是「这台机器是什么」，无法表达
   「我要生成另一台机器的代码」。
2. **`--host` 已彻底去掉，改由 config.guess 原生识别。** 实测上游自带的
   config.guess（timestamp 2014-11-04）在本机**直接失败**（`uname -s` 返回
   `HarmonyOS`，脚本报 `unable to guess system type`，rc=1）；这正是官方
   `scripts/patch-autotools-ohos.pl` 存在的原因。该脚本对本项目只命中 **1/5**
   （config.sub 三处全不命中，config.guess 插入的块也不生效 —— 见下面第 1 条），
   因此改为按本文件风格手工最小改写。

去掉 `--host` 之后，configure 不再走交叉分支，带来一个实测收益：`CC_FOR_BUILD`
自动解析为 `$CC`（/data/service/hnp/bin/clang），构建期生成器 `mkext` 无需任何
额外干预 —— 之前用 `--host` 时需要在配方里补 `chmod 0755` 并显式传
`CC_FOR_BUILD="$CC"`。本包现在没有这些绕过代码。

configure 实测输出：

```
checking host system type... aarch64-unknown-linux-ohos
checking target system type... x86_64-pc-linux-gnu
Target CPU is .................... amd64
Target OS is ..................... linux
Compiler is called ............... amd64-linux-pcc
```

## 三、上游测试清点与实测（R51 三步法）

### 1. 清点（真实核查依据）

- 上游顶层 `Makefile` 与 `cc/Makefile` **都没有** `check` / `test` 目标；上游**不存在**
  `make check`。
- 唯一测试套件：`cc/cpp/tests/`，由 `cc/cpp/Makefile.in` 的 `test` 目标驱动：
  `for n in 1..18`，逐个 `./$(DEST) < tests/test$n > tests/run$n && cmp run$n res$n`；
  并对存在 `res${n}C` 的用例追加一次 `-C`（保留注释）运行与比对。
- 有效比较数 = **18（test1..test18）+ 2（test15C、test16C）= 20**。
- 目录里另有 `test19`/`test20`/`test21`，但**没有**对应 `res19`/`res20`/`res21`，
  上游 `test` 目标也不遍历它们，不计入。
- **该 `test` 目标的退出码不可信**：比较用 `;` 串联，`cmp` 失败也不会让 make 失败
  （实测即使人为破坏 res 文件，`make -C cc/cpp test` 仍返回 0）。因此配方在
  `build()` 里重新做一次逐项比较，不一致就 raise —— 否则这条测试是「恒真」的。

### 2. 实测结果（真机原生执行，非模拟）

```
UPSTREAM_RESULT pass=20 fail=0 total=20   →  通过率 20/20 = 100%
```

说明：`-C` 变体是对**同一输入**的另一次比较（期望输出为独立的 `res15C`/`res16C`），
按「比较次数」计为 20；若按「编号用例」计则为 18/18。两种口径都在此列明。

### 3. test_package（消费者视角）

`test_package/main.c` 是一个自足翻译单元（两个函数，其一在循环中调用另一个，不含
系统头文件），由打包后的 `amd64-linux-pcc` 真实编译并断言生成的汇编含 x86-64 目标
代码（`pushq` / `%rbp` / `movl`）。实测生成 992 字节汇编，断言全中。

## 四、四个补丁分别解决什么

### 0001 — config.guess / config.sub 认识 HarmonyOS

`config.guess` 增加 `*:HarmonyOS:*:*` 分支：

```sh
    *:HarmonyOS:*:*)
	case "$UNAME_MACHINE" in
	    aarch64|arm64) MACHINE=aarch64 ;;
	    armv7*|armv8*) MACHINE=arm ;;
	    x86_64|amd64)  MACHINE=x86_64 ;;
	    i?86)         MACHINE=i686 ;;
	    *)            MACHINE="$UNAME_MACHINE" ;;
	esac
	echo ${MACHINE}-unknown-linux-ohos
	exit ;;
```

> 注意：**这份 config.guess 的每个分支都必须自带 `echo` + `exit`**（文件末尾是
> 「unable to guess system type」错误块），官方 `patch-autotools-ohos.pl` 插入的块
> 只赋值 `GUESS` 不输出不退出，在本文件上会静默失效 —— 这是该脚本对本项目只命中
> 1/5 的主要成因之一。

`config.sub` 增加 `linux-ohos*` 到 kernel-OS 列表与 OS 类型列表（两处最小改动，
官方脚本用的 `android-linux` / `linux-uclibc` 锚点在本文件中不存在）。

实测（补丁后）：`sh ./config.guess` → `aarch64-unknown-linux-ohos`；
`sh ./config.sub aarch64-unknown-linux-ohos` → 原样接受。
补丁前：config.guess rc=1；config.sub 报
`machine 'aarch64-unknown-linux' not recognized` / `system 'ohos' not recognized`。

### 0002 — 驱动中间文件遵循 $TMPDIR

上游 `cc/cc/cc.c` 的 `gettmp()` 把临时文件模板硬编码为 `/tmp/ctm.XXXXXX`。
鸿蒙的 `/tmp` 是 **erofs 只读挂载**（知识库 E002，官方推荐方案就是设 `TMPDIR`），
于是**任何非 `-E` 的编译都会失败**：

```
error: /tmp/ctm.XXXXXX: Read-only file system
```

本补丁让 `gettmp()` 优先使用 `$TMPDIR`、缺省回退 `/tmp`。这不是新造机制：上游自己
未启用的 `cc/driver/driver.c:281` 就是 `template = getenv("TMPDIR");`，本补丁把
在用的驱动对齐到上游既有约定。

### 0003 — x87 内联汇编限定到 x86 主机

`arch/amd64/code.c` 顶部无条件用 `fstcw`/`fldcw` 设置 x87 控制字，aarch64 主机
clang 报 `unrecognized instruction mnemonic`。上游自己在该处标了
`/* XXX cross-compiling will fail here */`。按「追加平台条件、不删原逻辑」收窄为
`__i386__`/`__x86_64__`。

### 0004 — `configure` 的临时目录不再用 `umask 077`

autoconf 生成器在 `configure` 与它生成的 `config.status` 里都用同一段代码创建临时目录：

```sh
{
  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
  test -d "$tmp"
}  ||
{
  tmp=./conf$$-$RANDOM
  (umask 077 && mkdir "$tmp")
} || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5
```

鸿蒙/HMDFS 对目录强制 setgid，于是 `umask 077` 下建出的是 `drwx--S---`（2700），
**即使属主是自己也写不进去**，且 `chmod` 也改不动（知识库 E114）。结果是 `configure`
末尾生成 `config.status` 时直接死掉：

```
./config.status: line 612: ./conffCGiDm/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

本补丁去掉这两处 `umask 077`（第二处连带的 `2>/dev/null` 与上游先例一致），
使临时目录以普通权限创建。本机实测：补丁前 `configure` 稳定 rc=1（连跑 3 次全挂），
补丁后在干净源码树上连跑 3 次全部 rc=0 并生成 `Makefile`、`cc/cpp/Makefile` 等。

> 说明：这条是**平台 CI 真实构建**暴露、本地用 PATH 前置 `umask 022` 的 `mktemp` shim
> 绕过过的坑；绕过只解决本机，配方必须自带修正才能在 CI 干净环境成立。

## 五、构建参数里保留的 `-fcommon` 与 `-static`（均经实测）

- **`-fcommon` 必需**：去掉后 `ld.lld: error: duplicate symbol: lineno`，
  make rc=2（`mip/common.c` 与生成的 `scan.c` 都定义了 `lineno`；GCC≥10 / clang≥11
  默认 `-fno-common`）。
- **`-static`**：OHOS 动态链接产物在构建机上无法执行（E544，缺
  `/lib/ld-musl-aarch64.so.1`）；静态链接使包在被测平台之外也可运行，
  并去掉对 musl 加载器路径的耦合。

## 六、真机环境观察（如实记录，非缺陷）

- `make install` 使用上游默认的 `INSTALL_PROGRAM = ${INSTALL} -s`，本机 rc=0 无报错；
  但本机 `/bin/install` 是 toybox，实测 `-s` **被静默忽略**，安装后的二进制仍是
  unstripped（972736 字节，`readelf -S` 仍有 symtab）。这是平台行为，配方不再像
  早期 Windows 版本那样额外调用 strip 去「修正」它。
- `-v` 的退出码为 8（pcc 自身约定），不是 0。

## 七、验证链路（本机实测）

```
conan create（完整，含 test_package）
  ├─ 源码 sha256 校验（f4fc6586…46daf）    PASS
  ├─ 四个补丁在干净源码上应用               PASS
  ├─ configure（host 由 config.guess 原生识别）PASS
  ├─ make（6 个可执行产物）                 PASS
  ├─ 上游测试 20 次比较 / 0 失败            PASS
  ├─ 产物架构 = AArch64 静态 ELF            PASS
  └─ 消费者测试（真机原生编译，992 字节汇编）PASS
```
---

**编译结束**: 2026-10-02 19:21
**最终状态**: built
