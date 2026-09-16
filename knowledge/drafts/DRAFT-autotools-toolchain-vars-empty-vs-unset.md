# DRAFT-autotools-toolchain-vars-empty-vs-unset — `${VAR-default}` 与「空串」：误导性的 `no NEON support`

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-13
> **Severity**: 🟡 medium | **Category**: build-system / toolchain / autotools / environment

## 症状

x264（手写 `configure` + 汇编优化）在 CI 上 configure 阶段失败：

```
no NEON support, try adding -mfpu=neon to CFLAGS
If you really want to run on such a CPU, configure with --disable-asm.
```

而**完全相同的参数**在本机（/data）、HMDFS 目录、以及真机手工构建**全部通过**（`asm: yes`）。

## 一条关键的判别特征

该次失败的 configure **stdout 只剩上面那两行**。

原因：configure 的绝大多数检查把结果写 **stderr**（`log_ok`/`log_fail`/`log_msg` 都重定向到 `config.log`），
只有 `as_check` 失败时那两句 `echo` 走 **stdout**。所以——

> **stdout 只剩两行 ⇒ 死在 `as_check`，而不是别的阶段。**

这条特征能立刻排除"缺头文件""编译器版本不对"等等猜测。

## 根因

`as_check` 把待测指令写进 `conftest$AS_EXT` 再交给 `$AS`：

```sh
as_check() {
    echo "$1" > conftest$AS_EXT
    as_cmd="$AS conftest$AS_EXT $ASFLAGS $2 -o conftest.o"
    $as_cmd >conftest.log 2>&1
    ...
}
if as_check "cmeq v0.8h, v0.8h, #0" ; then
    define HAVE_AARCH64; define HAVE_NEON
else
    echo "no NEON support, try adding -mfpu=neon to CFLAGS"
    exit 1
fi
```

而 `$AS` 的来源是：

```sh
AS="${AS-${CC}}"          # x264 configure:846（aarch64 分支）
```

**这是 POSIX 的「未设置才回退」**：`${VAR-default}` 只在 `VAR` **未设置**时取 default。
若 `VAR` 已设置但为**空串**，取到的就是空串 —— **不会**回退。

于是当调用方把 `AS` 导出成空串时：

* `$AS` 为空 → `as_cmd` 变成 `" conftest.S -I... -c -o conftest.o"`
* shell 把开头的 `conftest.S` 当成**要执行的程序**（汇编源文件当然不可执行）
* `as_check` 失败 → 走 `else` 分支 → 打出那条**把矛头指向 NEON 的**错误并 `exit 1`

> **注意**：那段错误文本与 NEON **毫无关系**。`else` 分支不看任何 NEON 探测结果，
> 它只代表"这一条命令失败了"。`-mfpu=neon` 在 aarch64 上也不适用。

同一个坑对 **`AR`**、**`STRIP`** 同样成立（configure 里分别是
`AR="${AR-${cross_prefix}gcc-ar}"`、`STRIP="${STRIP-${cross_prefix}strip}"`），
所以**只补 `AS` 是治标**。

### 空串通常从哪来

* CI worker 的 buildenv / 环境快照里带着占位导出（`export AS=`）
* ccache / distcc 一类包装脚本
* 用户的 `.zshrc` / `.profile` 里的占位赋值

## 复现矩阵（受控：同一源码、同一目录，只变 `AS` 的导出状态）

| `AS` 状态 | rc | configure stdout | 结果 |
|-----------|----|-----------------|------|
| 未设置（基线） | 0 | 27 行 | `asm: yes` |
| `AS=<hnp>/as` | 0 | 27 行 | 正常（`as` 也能过） |
| **`AS=`（空串）** | **1** | **2 行** | **`no NEON support...`** ← 与 CI 日志逐字一致 |
| `AS=` 空串 **+ 显式 `AS=clang`** | **0** | 27 行 | `asm: yes` ← 修法生效 |

直接验证 `-default` 语义：

```sh
bash -c 'AS=;       echo "AS=${AS-fallback}"'   # 打印空行   —— 空串不回退
bash -c 'unset AS;  echo "AS=${AS-fallback}"'   # 打印 fallback —— 未设置才回退
```

## 修法

**在配方调用 configure 的命令行上内联显式赋值全部工具链变量为绝对路径**，
不依赖任何继承来的环境（R33）：

```python
tools = {
    "CC":     <conf tools.build:compiler_executables["c"]>  or <hnp>/clang,
    "AS":     同上,
    "AR":     <hnp>/llvm-ar,
    "RANLIB": <hnp>/llvm-ranlib,
    "NM":     <hnp>/llvm-nm,
    "STRIP":  <hnp>/llvm-strip,
}
self.run('{} INSTALL=/bin/install TMPDIR="{}" "{}" "{}" {}'.format(
    tools, tmp, bash, configure, args))
```

实测命令行形态：

```sh
CC=/data/service/hnp/bin/clang AS=/data/service/hnp/bin/clang \
AR=/data/service/hnp/bin/llvm-ar RANLIB=/data/service/hnp/bin/llvm-ranlib \
NM=/data/service/hnp/bin/llvm-nm STRIP=/data/service/hnp/bin/llvm-strip \
INSTALL=/bin/install TMPDIR="<build>/_tmp" \
/data/service/hnp/bin/bash <src>/configure --host=aarch64-unknown-linux-gnu --enable-shared ...
```

**回归验证**：以 `AS= conan create ...` 模拟该 worker 环境 → rc=0、无 NEON 错误、
checkasm 仍 2 次 `x264: All tests passed Yeah :)`、test_package 6/6 全过。

## 为什么不该用 `--disable-asm` 绕过

错误提示自己就建议了 `--disable-asm`，但那是**把可修的问题降级为功能损失**：

* `as_check` 失败是"变量取到空值"的表征，**不是**"CPU 不支持 NEON"
* 加 `--disable-asm` 会真的丢掉全部 aarch64 汇编优化
* 本机 `asm: yes` 时可正常编译并跑通 **102 项** checkasm，证明汇编路径本身没问题

## 顺带：让失败可见

本次 CI 只留下那句 NEON 报错，而 configure 其实**已把失败命令原文与编译器 stderr
写进 `config.log`**。建议配方加失败兜底，把 `config.log` 尾部打到 CI 日志：

```python
try:
    self.run(cmd)
except ConanException:
    if os.path.isfile(os.path.join(self.build_folder, "config.log")):
        for line in open(...).read().splitlines()[-60:]:
            self.output.error(line)
    raise
```

否则定位只能靠猜或本地复现（本次即如此）。

## 适用范围

任何「上游 configure 用 `${VAR-default}` 取工具链变量」的 autotools / 手写 configure 项目
（x264、libvpx、各类带汇编优化的多媒体库），在 CI 或陌生构建机上出现该错误签名时均可套用。
判别顺序：

1. 看 configure **stdout 是否只剩 2 行**（⇒ 死在 as_check）
2. 看 `config.log` 里 `Failed commandline was:` 那行（⇒ `$AS` 是否为空 / 异常）
3. 在配方里把 `CC/AS/AR/RANLIB/NM/STRIP` 全部固定为绝对路径

## 诚实标注（limitations）

1. **"真凶是空串"是基于行为一致性的强推断，非直接取证** —— worker 的文件系统与本地隔离，
   拿不到它那一轮的 `config.log` / 环境快照。可信度依据是：空串是已知**唯一**能逐字复现
   该现象（含 stdout 只剩 2 行这个细节）的条件。
2. 但**处置本身独立成立** —— "显式固定工具链变量为绝对路径"同时消除"空串""被遮蔽"
   "继承污染"三类风险，属 R33 的正向加固；即使真凶另有其因也无害。
3. 该签名也可能由真实原因触发（目标 CPU 确实无 NEON、用了非 aarch64 汇编器等），
   故应按下节顺序判别，而非一律归因于空串。

## 相关

* `DRAFT-libpfm-4.13.0-make-sys-linux-gate`、`DRAFT-infoware-cpuid-arch-guard`
  —— 同属"aarch64 上架构相关代码被错误路径带偏"，但根因不同（那两条是架构宏/守卫缺失）
* E518（CI worker `git-clone` 缺 `libz.so`）—— 同一轮 CI 出现的**另一个独立** worker 环境问题，
  与本条无关
