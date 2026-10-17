# libf2c2 20240504 适配笔记

## 编译环境

- 构建系统: makefile（上游 `makefile.u`，无 configure/CMake/meson 层）
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4（OHOS SDK，`/data/service/hnp/bin/clang`）
- 目标: OpenHarmony PC aarch64（conan profile `ohos-aarch64`，os=OHOS / arch=armv8）
- 状态: built

## 软件与版本溯源

libf2c2 是 f2c 的 Fortran 运行时库：f2c 把 Fortran 转成 C，内在函数、字符串
处理和整套格式化/列表定向 I/O 运行时都留在本库里，转译结果用 `-lf2c` 链接。

netlib 只发布无版本号的固定文件名，没有带版本的 release 包：

```
https://netlib.org/f2c/libf2c.zip    # 共 184 个文件（160 个 .c + 头文件 + makefile.u），本包源码
https://netlib.org/f2c/src.tgz       # f2c 编译器自身源码，非本包范围
```

版本号 `20240504` 的出处是 Debian：Debian 的源码包 `libf2c2` 版本 `20240504-1`
就是把这个 zip 原样打包成 orig tarball 后使用的上游版本号，其
`libf2c2_20240504-1.dsc` 的 `Homepage` 为 <https://netlib.org/f2c/>，`debian/copyright`
的 `Source` 为 `ftp://netlib.bell-labs.com/netlib/f2c`。因此用这个版本号既能
对上任务清单，又能指向唯一上游。核实过程（本次实测）：

```bash
$ curl -sS -o libf2c.zip https://netlib.org/f2c/libf2c.zip
$ sha256sum libf2c.zip
cc84253b47b5c036aa1d529332a6c218a39ff71c76974296262b03776f822695

$ curl -sSL -o libf2c2_20240504.orig.tar.xz \
    https://deb.debian.org/debian/pool/main/libf/libf2c2/libf2c2_20240504.orig.tar.xz
$ sha256sum libf2c2_20240504.orig.tar.xz
85989f4f1ec3db3b1581bd16a807be3bb3a1f547f7fe7ba4e074d02710521aef

$ unzip -qq libf2c.zip -d ours && tar xJf libf2c2_20240504.orig.tar.xz -d deb
$ diff -rq ours deb/libf2c2-20240504 && echo IDENTICAL
IDENTICAL                      # 两侧各 184 个文件，逐字节相同
```

所以 conandata.yml 里固定的 netlib zip 就是 20240504 这一版的上游内容，
该 sha256 同时锁死了内容和版本。Debian 的二进制包在此之上还叠加了
`debian/patches`（C.LAPACK 的 `i_ceiling.c`/`i_len_trim.c`、weak MAIN__、
`XintXX_t`、cross 等），那些是 Debian 下游打包行为，不属于上游源码，
本配方不引入——导出符号差异见下文。

## 编译步骤

上游 `makefile.u` 是 in-source 构建，配方按 Debian 的参考调用方式驱动它：

```bash
# 1) 生成派生头文件（上游 makefile 的规则，f2c.h 按 README 做 LP64 调整）
sed 's/long int /int /' f2c.h0 > f2c.h    # 本机 sizeof(long)==8，见下一节
cp signal1.h0 signal1.h; cp sysdep1.h0 sysdep1.h; cp fio.h0 fio.h

# 2) 目标码 + 静态库（arith.h 由 arithchk.c 现场编译并运行生成）
make -f makefile.u -j2 CC=clang \
     CFLAGS="-O2 -fPIC -DNON_UNIX_STDIO" libf2c.a

# 3) 共享库（与参考打包一致，保留上游 ABI 名）
clang -shared -Wl,-soname,libf2c.so.2 -o libf2c.so.2.1 *.o -lm
```

`-DNON_UNIX_STDIO` 是上游 `makefile.u` 文件头对 Linux 目标的要求（单位文件的二进制模式 I/O）。
默认的 `flag`/`ftnlen`/`ftnint` ABI 由「不定义 `f2c_i2`」选中——`f2c.h` 只有
`#ifdef f2c_i2` 一个分支判据，上游源码中没有任何代码消费一个裸 `f2c` 宏，因此配方不传多余的 `-D`。

**为什么 f2c.h 要做 LP64 调整**：`f2c.h0` 把 `integer`/`logical`/`flag`/
`ftnlen`/`ftnint` 定义为 `long int`。上游 README 明确说明，在
`sizeof(short)==2 && sizeof(int)==sizeof(float)==4 && sizeof(long)==sizeof(double)==8`
的机器上（本目标即如此，aarch64 OHOS）必须改为 `int`，并给出上面那条 sed。
不改会让 Fortran 的 INTEGER 变成 8 字节，与 Fortran 默认 INTEGER 语义和
所有既有 f2c 生成代码都不兼容。生成的 `f2c.h` 与库一起安装，头文件与
二进制 ABI 因此始终一致。

**arith.h 由目标机原生生成**：`uninit.c` 依赖 `arith.h`，上游用
`arithchk.c` 现场编译并执行来推导（`IEEE_8087`、`Long int`、`QNaN*` 等）。
本任务 profile 是在 OHOS/aarch64 上原生编译，所以这一步直接可用，
不需要交叉编译时常见的"宿主机预生成 arith.h"绕行。实测生成内容：

```
#define IEEE_8087
#define Arith_Kind_ASL 1
#define Long int
#define Intcast (int)(long)
#define Double_Align
#define X64_bit_pointers
#define QNaN0 0x0
#define QNaN1 0x7ff80000
```

**libf2c_i2 未构建（范围决定）**：Debian 的二进制包 `libf2c2` 里还有
`libf2c_i2.so.2`，那是给 `f2c -i2` 生成代码用的 ABI（`f2c.h` 的
`#ifdef f2c_i2` 把 `flag`/`ftnlen`/`ftnint` 变成 short）。本仓库没有
f2c 编译器包，生态里没有产生 `-i2` 代码的来源；而且两个 ABI 导出完全
相同的符号名，无法共用同一条链接命令。需要时可照上面步骤加
`-Df2c_i2` 再编译一遍，并把产物命名为 `libf2c_i2.so.2`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `uninit.c:236: fatal error: 'fpu_control.h' file not found`，默认 `OFILES` 的 154 个目标文件里唯一编不过的一个（另有 6 个 .c 上游默认不编：arithchk.c 只在生成 arith.h 时编译执行，signbit.c 需 -DSIGNED_ZEROS，ftell64_/pow_qq/qbitbits/qbitshft 属可选 INTEGER*8 支持组） | `fpu_control.h` 是 glibc 专有头文件，OHOS sysroot 用 musl 没有它；OHOS clang 仍定义 `__linux__`，于是 `#ifdef __linux__` 误入了 glibc 分支 | `patches/0001`：把该保护的判据收窄为 `defined(__linux__) && defined(__GLIBC__)`。glibc 上行为不变；musl 上落到上游自带的 `ieee0() {}` 回退分支（上游对所有非 Linux 目标本来就用它）。未引入任何 `__OHOS__` 宏，功能未删：只是 `-trapuv` 的浮点异常解除屏蔽在非 glibc 上不可用，与其它非 glibc 系统一致 |
| 2 | 链接共享库失败：`ld.lld: error: undefined reference due to --no-allow-shlib-undefined: MAIN__` | 上游把 `main.c` 编进库里，而 `MAIN__` 由转译程序提供，于是 `libf2c.so` 留下未定义符号；lld 与新版 binutils 默认拒绝链接含未定义符号的 .so | `patches/0002`：`main()` 声明 weak，`MAIN__` 用 weak alias 指向一个返回 -1 的本地实现。转译程序里的强 `MAIN__` 仍然覆盖它，普通 C 程序的 `main` 也不会被库抢走。这与 Debian 记录的同一缺陷（#826253）是同一个修复 |
| 3 | 静态库链接正常、共享库链接被拒（问题 2 的表象） | 静态库按需抽取成员，`main.o` 不被拉入时未定义符号不出现，问题被掩盖 | 见问题 2。CI 与实际交付走的是默认选项 `shared=True`，test_package 因而只覆盖共享链接，并额外覆盖"转译程序形态"（自身无 `main`）；静态链接是在适配阶段的设备手工实测中一并验证的，命令与输出见下文「验证结果」，该次手工实测未保留独立原始日志文件 |

## 源码修改

| 补丁 | 文件 | 修改内容 |
|------|------|----------|
| `patches/0001-uninit-guard-fpu-control-on-glibc.patch` | `uninit.c` | 1 行：`#ifdef __linux__` → `#if defined(__linux__) && defined(__GLIBC__)` |
| `patches/0002-main-weak-entry-points.patch` | `main.c` | 20 行新增：`main()` 声明 weak；`MAIN__` 通过 `__attribute__((weak, alias("weak_MAIN__")))` 获得 weak 定义 |

两个补丁都不含平台宏，都是把上游已经存在的可移植性缺口按 POSIX/工具链
通用方式补上，不改变任何上游功能语义。

## 依赖版本

无 Conan 依赖（纯 C，只用 libc/libm；`cpp_info.system_libs = ["m"]`）。
W0 预检：`libf2c2/20240504` 在 ohpcd 制品仓未被占用（`version_occupancy: missing`），
依赖清单显式为空，`dependency_source: explicit`，报告状态 `pass`。

## 验证结果

设备（OHOS aarch64，原生 clang）实测，全部通过：

```bash
# 上游 makefile.u 构建
$ make -f makefile.u -j2 CC=clang CFLAGS="-O2 -fPIC -DNON_UNIX_STDIO" libf2c.a
ar r libf2c.a <154 objects ...>
ranlib libf2c.a
$ echo $?
0
$ ls -l libf2c.a
343030 bytes

# 共享库链接（SONAME 保留上游 ABI 名）
$ clang -shared -Wl,-soname,libf2c.so.2 -o libf2c.so.2.1 *.o -lm && echo ok
ok
$ ls -l libf2c.so.2.1
117056 bytes

# 消费者测试 A：静态链接
$ clang -O2 -I. -o t_static test_package/test_main.c libf2c.a -lm && ./t_static
... 27 项 ok ...
all checks passed
$ echo $?
0

# 消费者测试 B：共享链接
$ clang -O2 -I. -o t_shared test_package/test_main.c -Lslib -lf2c -lm -Wl,-rpath,$PWD/slib && ./t_shared
... 27 项 ok ...
all checks passed
$ echo $?
0

# 转译程序形态（自身不定义 main，只定义 MAIN__）
$ clang -O2 -I. -o t_start test_package/test_startup.c libf2c.a -lm && ./t_start
 12345
$ echo $?
0
```

`test_main` 的 27 项断言全部走库的真实导出符号：`d_prod`/`pow_dd`/`d_lg10`/
`i_nint`/`d_sign`（内在函数）、`s_cmp`/`s_copy`/`i_indx`（字符串运行时）、
`_uninit_f2c`（-trapuv 辅助，验证仍把未初始化值填成 NaN）、以及
`f_open`/`s_wsle`/`do_lio`/`e_wsle`/`f_clos`/`s_rsle`/`e_rsle` 组成的
列表定向文件写入-关闭-重开-读回往返。`test_startup` 验证入口点、
`f_init()` 与 `atexit(f_exit)` 来自库内 `main.c`，程序只提供 `MAIN__`。

**导出符号与参考打包比对**（`nm -D --defined-only`）：

```
本包 libf2c.so.2.1 : 281 个（含工具链的 _init/_fini）
Debian libf2c.so.2.1: 283 个
Debian 独有：i_dceiling、i_sceiling、i_len_trim（0004-add-clapack-files.patch
             新增 i_ceiling.c/i_len_trim.c）、unsupported_error（0003-C-tweaks.patch）
本包独有：_init、_fini（ELF 节符号，非库 API）
```

即除 Debian 自己叠加上去的下游补丁外，本包对上游 `makefile.u` 默认
`OFILES` 的导出面与参考打包完全一致（其余 279 个符号逐个相同）。

**上游测试情况**（R51 三步法）：`libf2c.zip` 内不含可运行的功能测试程序。
唯一入口是 `makefile.u` 的 `check` 目标，作用是把 182 个源文件与随包文件的 xsum
校验和与包内 `xsum0.out` 比对（传输完整性检查），且需要 `xsum` 工具，
而 `xsum.c` 属于独立的 f2c 编译器源码包（netlib `src.tgz`），不在本压缩包内，
因此在库里无法执行。源文件完整性由 conandata.yml 的 sha256 固定，
强度不低于该 xsum 比对。消费者验证全部由 `test_package/` 承担（见上）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `lib/libf2c.so.2.1` | 117056 | 共享库实体，SONAME `libf2c.so.2` |
| `lib/libf2c.so.2` | 符号链接 | SONAME 名 |
| `lib/libf2c.so` | 符号链接 | `-lf2c` 链接名 |
| `lib/libf2c.a` | 343030 | 静态库（`shared=False` 时安装） |
| `include/f2c.h` | 223 行 | 与库同源生成的 LP64 头文件 |
| `licenses/Notice` | — | AT&T / Lucent / Bellcore 许可声明 |

## 注意事项

- 头文件必须与库成对使用。`f2c.h` 由本包 `f2c.h0` 调整而来，安装版本与
  编译库时使用的那一份完全一致；换成 Debian `libf2c2-dev` 的 `f2c.h`
  （改用 `int32_t/int16_t`）在同尺寸平台上 ABI 等价，但本包不采用，
  因为它属于 Debian 的打包改动而非本压缩包内容。
- 共享库导出 `main` 与 `MAIN__`（均为 weak）。想用库自带入口点的转译
  程序不要自己再定义 `main`；普通 C 程序定义自己的 `main` 不受影响。
- `-DNON_UNIX_STDIO` 会改变单位文件的打开模式（二进制模式），这是上游
  对 Linux 的既定建议，与 Debian 一致。
