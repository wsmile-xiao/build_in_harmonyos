# E580 — 交叉 GCC 在 OHOS 上的三处必修绕坑（内置前置库 config.sub / STMP_FIXINC / 目标 as·ld·nm 垫片）

## 错误特征

在 HarmonyOS（宿主 aarch64-linux-ohos）上构建 **GNU GCC 交叉编译器**时，按出现顺序可能出现三类互不相同的报错；只修其中一处，后续两处仍会让构建或测试确定性失败：

**① 内置前置库拒绝 OHOS 三元组（configure 阶段）**

```
configure: error: /path/build/gmp/config.sub aarch64-unknown-linux-ohos failed
make: *** [Makefile:4843: configure-gmp] Error 1
```

**② fixincludes 在 HMDFS 上重复触发（make 阶段）**

```
shell-init: error retrieving current directory: getcwd: cannot access parent directories: Not supported
chdir: error retrieving current directory: getcwd: cannot access parent directories: Permission denied
pwd: error retrieving current directory: getcwd: cannot access parent directories: Invalid argument
make: *** [Makefile:3246: stmp-fixinc] Error 1
```

**③ 驱动误用宿主汇编器/链接器（test_package 或用户编译阶段）**

```
Assembler messages:
Error: unknown architecture `armv4t'
Error: unrecognized option `-march=armv4t'
```

## 触发条件

- 构建系统: autotools（GCC 自带顶层 `configure` + 子目录 configure）
- 阶段: ①`configure`（顶层启动即触发）②`make all-gcc` / `make -C gcc selftest` 等任何依赖 `stmp-int-hdrs` 的目标 ③`test_package` 或任何用打包后驱动编译的环节
- 平台: HarmonyOS PC（HMDFS 文件系统 + OHOS 拒绝执行未签名 ELF）
- 目标: 交叉目标（本文实测 `arm-none-eabi`，裸机，`--with-newlib --without-headers`）

## 根因分析

三处根因彼此独立，不能用同一招解决：

**① 顶层补丁不够：GCC 会用每个内置前置库自己的 `config.sub`**

GCC 顶层 `configure` 在规范化 build 三元组时，会**逐个执行**树内前置库（`gmp/`、`mpfr/`、`mpc/`）自带的 `config.sub`。因此只给顶层 `config.guess`/`config.sub` 打平台识别补丁**不足以**通过——这些前置库发布年代久远（`gmp 6.1.0` 为 2015 年，`mpfr 3.1.6`、`mpc 1.0.3` 同代），不认识 `aarch64-unknown-linux-ohos`，直接让 `configure-gmp` 失败。

实测判据（同一三元组、同一文件位置对比）：

```
$ bash <patched-top-level>/config.sub aarch64-unknown-linux-ohos   → aarch64-unknown-linux-ohos   (exit 0)
$ bash <bundled>/gmp/config.sub       aarch64-unknown-linux-ohos   → (拒绝, exit 1)
```

**② GCC 自身声明"交叉构建不能跑 fixincludes"，但 `STMP_FIXINC` 默认仍启用**

GCC 11.5.0 `gcc/configure.ac` 原文即为：

> When building gcc with a cross-compiler, we need to adjust things so that the generator programs are still built with the native compiler. **Also, we cannot run fixincludes.**

但 `STMP_FIXINC=stmp-fixinc` 仍被无条件写入，于是 `stmp-int-hdrs` 依赖 `stmp-fixinc`。OHOS 上必须对生成的宿主工具（`fixincl` 等）做 ELF 签名，**签名会刷新 `fixincl` 的时间戳**，使 `gcc/stmp-fixinc` 过期 → 重复执行 `fixinc.sh`。该重跑在 HMDFS 上不稳定：`fixinc.sh` 内部切目录/建临时目录，触发 `getcwd: Not supported / Permission denied / Invalid argument`，最终 `make: *** [Makefile:3246: stmp-fixinc] Error 1`。

> 关键在于这是**"签名→时间戳失效→重跑不可靠规则"的连锁反应**，不是 fixincludes 本身逻辑错。

**③ GCC 按"无前缀名"在自身 exec prefix 里找 as/ld，宿主 PATH 里恰好也有一个 as**

GCC 查找汇编器/链接器时，**先在自己的 exec prefix（`GCC_EXEC_PREFIX`、`-B` 目录）里找无前缀名 `as`、`collect-ld`、`nm`**，找不到才回落 PATH。OHOS 宿主的 PATH（如 `/data/service/hnp/bin`）里存在 AArch64 的宿主 `as`，而 binutils 包（如 `arm-none-eabi-binutils`）只提供**带前缀**的 `arm-none-eabi-as`、`arm-none-eabi-ld`、`arm-none-eabi-nm`。于是驱动命中宿主 `as`，把目标代码当宿主汇编处理：`unknown architecture 'armv4t'`。

实测判据（同一驱动、同一源文件，只改变垫片是否存在）：

```
# 无垫片: test_package 编译失败
$ arm-none-eabi-gcc -std=c17 -O0 -c smoke.c      → Assembler messages: Error: unknown architecture `armv4t'
# 在 <pkg>/libexec/gcc/arm-none-eabi/11.5.0/ 放入 as/ld/nm 垫片后:
$ arm-none-eabi-gcc -std=c17 -O0 -c smoke.c      → exit 0（产出 elf32-littlearm 目标文件）
```

## 解决方案

### 推荐方案（三处同时修）

**① 把已打补丁的顶层 config 脚本注入每个内置前置库**（在 `source()` 内，`apply_conandata_patches` 之后）：

```python
for name in ("gmp", "mpfr", "mpc"):
    for script_name in ("config.guess", "config.sub"):
        shutil.copyfile(os.path.join(root, script_name),
                        os.path.join(root, name, script_name))
```

**② make 命令行传 `STMP_FIXINC=`（空值会传播到所有子 make）**：

```python
make_command = "{} --jobserver-style=pipe -j{} STMP_FIXINC=".format(make, jobs)
```

`STMP_FIXINC` 为空后 `stmp-int-hdrs` 不再依赖 `stmp-fixinc`，fixincludes 与 `fixinc.sh` 完全不参与交叉构建——这正是 GCC 自己注释所描述的行为；对 `--with-newlib --without-headers` 的裸机目标本就没有目标系统头可复制。

**③ 在构建期与打包期都放好无前缀垫片**：

```sh
# D=<pkg>/libexec/gcc/<target>/<version>
printf '#!/bin/sh\nexec arm-none-eabi-as "$@"\n'      > "$D/as";         chmod 755 "$D/as"
printf '#!/bin/sh\nexec arm-none-eabi-ld "$@"\n'      > "$D/ld";         chmod 755 "$D/ld"
printf '#!/bin/sh\nexec arm-none-eabi-ld "$@"\n'      > "$D/collect-ld"; chmod 755 "$D/collect-ld"
printf '#!/bin/sh\nexec arm-none-eabi-nm "$@"\n'      > "$D/nm";         chmod 755 "$D/nm"
```

构建期还需在构建树的 `gcc/` 内放同名垫片（GCC 构建时会先在这些目录里找）；打包期垫片必须落在安装后的 `libexec/gcc/<target>/<version>/`，因为驱动运行时搜索的是该 exec prefix。

### 禁止做法

- ❌ 只给顶层 `config.guess`/`config.sub` 打补丁就认为交叉三元组已解决（内置前置库会用**自己的**拷贝再次拒绝）
- ❌ 直接 `rm -rf fixincl` / 删 `fixincludes` / `chmod` 掩盖，或接受 `getcwd` 到 stderr 当作无害噪音（抑制症状，另两处失败仍在，且可能掩盖真实的缺头文件缺陷）
- ❌ 把宿主 PATH 里的宿主 `as` 挪走/改名当作修复（污染共享环境，且 CI worker 不可控）

## 验证

```bash
# ① 交叉三元组：顶层与内置前置库都必须接受
bash <tree>/config.sub       aarch64-unknown-linux-ohos   # 期望: aarch64-unknown-linux-ohos
bash <tree>/gmp/config.sub   aarch64-unknown-linux-ohos   # 期望: aarch64-unknown-linux-ohos（注入后）

# ② fixincludes 已停用：make 命令行含 STMP_FIXINC=，日志无 stmp-fixinc 重跑报错
grep -n 'STMP_FIXINC=' conanfile.py
grep -c 'stmp-fixinc\] Error' <build-log>                  # 期望: 0

# ③ 垫片生效：驱动编译目标代码成功且产物为 elf32-littlearm
ls <pkg>/libexec/gcc/<target>/<version>/{as,ld,collect-ld,nm}
<pkg>/bin/<target>-gcc -c smoke.c -o smoke.o && <target>-objdump -f smoke.o
# 期望: exit 0 且输出含 "elf32-littlearm" 与 "architecture: arm"
```

实测环境（本条目来源）：HarmonyOS PC（aarch64-linux-ohos），`gcc-11-cross/26` = GNU GCC 11.5.0，目标 `arm-none-eabi`（`--with-newlib --without-headers --disable-bootstrap`）；`conan create` exit 0，`ci/conan/build_and_test.sh` L0/L1 通过。上游测试以 DejaGNU 套件为主口径（`gcc/testsuite/gcc/gcc.sum`：**53698 PASS / 0 FAIL**）；本条目回退路径的 `gcc.c-torture/{execute,compile}` 无系统头适用用例 **6506/6506 判定通过**（3253 源 × `-O0`/`-O2`，编译 + 目标 ELF 静态检查口径），两者口径不同、不可互相替代。

## 关联条目

- 相关: E007（config.guess/config.sub 平台识别）、E011（HMDFS `umask 077` 临时目录不可写）、E386（noexec 源树上的能力探测 shell 与 getcwd 诊断）、E002（`/tmp` 只读 → 用私有 `TMPDIR`）、E046（HMDFS chmod 不生效）
- 同族先例: `archives/g/gcc/9.5.0`（native，同样需签名宿主工具与 `AS`/`LD` 覆盖）、`archives/a/avr-gcc-bootstrap/14.2.0`（AVR 交叉，同结构）
