# mpfi 1.5.4 编译笔记（HarmonyOS PC · 标准 Conan autotools）

同 1.5.2：autotools + libtool + gmp/mpfr 依赖，配方沿用 1.5.2 的全部
鸿蒙补丁性配置（VirtualRunEnv(scope="build")、LDFLAGS 前置、umask 修正、删 .la）。

## 上游测试

- tests/Makefile.am 的 check_PROGRAMS 共 **159** 个 t* 程序（1.5.4 tarball 实测：
  awk 提取 tabs…tget_version 区间去重计数）。
- tarball 自带 tests/*.dat 参考数据，`make check` 全真跑。
- 本机即 OHOS 目标机（self-hosted，`--build==--host`），测试可执行文件
  直接运行，**无任何交叉构建跳过**；musl 无已知 skip/xfail 项。
- **结果：159/159 PASS，0 SKIP（conan create 全程日志见 ~/tmp/mpfi-create15.log）**。
- 首跑有 3 个失败，全部定位为**上游自伤缺陷**（补丁修复，详见 patches/ 与
  知识草稿 DRAFT-E552）：
  - `texp10`：tarball 漏发 exp10.dat（EXTRA_DIST 也没列）→ 删 check_data
    引用，check_random（512 精度全程）保留真跑；
  - `tdiv_ext`：mpfi-tests.h 正确的 IIII 双输出 typedef 被注释 + type_iiii.c
    读取器从未完成（按 1 输出读数据、4 参调用 5 参函数→段错误）→ 恢复 typedef
    并重写 read_line_iiii/check_line_iiii 为双输出，50 个数据行全过；
    check_random 因 random_iiii 同样未完成而注释；
  - `trec_sqrt`：函数类型错配（mpfr 单值当区间函数）+ rec_sqrt.dat 三类数据错
    （十六进制指数 p-1 应为 p-4 差 8 倍、inexact flag 位错、NaN 端点行为与实现
    分歧）+ **src/rec_sqrt.c 真实别名 bug**（mpfi_rec_sqrt(x,x) 第一条
    mpfr_rec_sqrt 写 a->left（与 b->left 同内存）后第二条才读它，输入端点
    自毁；实测探针 x=[0.25,4]：step1 后 b->left 已被覆盖为 0.5，step2 得
    错误上界 1.414 而非 2）→ 修类型、修实现别名（临时变量先存双端点）、删
    10 行矛盾数据、修 3 处记法 + 2 处 flag，21 行真值断言保留。
  - type_iiii.c 双输出断言（2026-09-10 代码审查修复）：第二输出 got2 用
    独立 mpfi_t 接收，期望值先从槽位 [3] 复制到独立 expected2 再调
    f_IIII，断言 same_value(got2, expected2)——旧实现把槽位 [3] 同时当
    got2 输出缓冲和 expected2，函数覆盖后比较退化为自比；div_ext.dat
    50 行双输出数据行全过。
  - 对照实验（正反验证）：`mpfr_rec_sqrt(±0, RNDU)=+Inf`；`0xb.5p-1`=5.6568 ≠
    `0xb.5@-1`=0.7071；修复后全部 PASS。

## 源信息（任务 2 核实）

- URL：`https://perso.ens-lyon.fr/nathalie.revol/softwares/mpfi-1.5.4.tar.bz2`
  （作者 Nathalie Revol 官方页面；Homebrew homebrew-core 与 Repology 同用此
  URL 且 SHA256 一致。注意路径是 `softwares/`（复数）。
  gforge.inria.fr 旧地址已死；GitLab `-/archive/1.5.4` 是无 configure 的
  git 快照，**不是**官方发布 tarball，勿用）
- SHA256：`d20ba56a8d57d0816f028be8b18a4aa909a068efcb9a260e69577939e4199752`
- License：源码头 LGPL-2.1+（tarball 内 COPYING.LESSER 为 LGPL-3 文本、
  COPYING 为 GPL-3 文本，随包分发但库本身 LGPL-2.1-or-later）
- 构建：Autotools（tarball 自带 configure，无需 autoreconf）
- 依赖要求：GMP ≥ 4.1.0、MPFR ≥ 4.0.1（configure.ac 编译期断言；
  本仓 gmp/6.3.0.1、mpfr/4.2.2.1 远超）
- 安装产物：`include/mpfi.h`、`include/mpfi_io.h`、`lib/libmpfi.so*`（+ .a）、
  `lib/pkgconfig/mpfi.pc`
- mpfi.pc：`Libs: -lmpfi -lmpfr -lgmp`，Requires: gmp, mpfr
- SONAME：libtool 默认（无 -version-info 覆盖）→ `libmpfi.so.0`

## 链接形态（重要）

- 本仓 mpfr/4.2.2.1 只有**静态二进制**（.a，remote 与本地皆然）→ libmpfi.so
  静态并入 mpfr 码（符号全部 DEFINED、无 UNDEF mpfr、NEEDED 无 libmpfr），
  与 1.5.2 先例同款形态。gmp 为动态（NEEDED libgmp.so.10）。
- conanfile 显式 `LIBS=-lmpfr -lgmp`：gmp 包（--enable-cxx 版）的 cpp_info
  含 gmpxx，不裁剪会把 libc++_shared 拖进纯 C 库的 NEEDED（实测命中）。
- SONAME=libmpfi.so.0（libtool 默认，configure 无 -version-info）。

## 消费者/鸿蒙测试接线

- test_package 直接 clang 编译（不走 CMake）：PkgConfigDeps + cpp_info 双路
  合并 include（fcl 实撞教训）；TARGET_SO/TARGET_A 宏注入制品路径，
  test_ohos.c 运行期 readelf 验证 ELF64/AArch64/SONAME/NEEDED/.codesign/
  .note.ohos.ident/无宿主路径 + 真值包含 + fenv 契约，fail closed。
  readelf 解析（2026-09-10 代码审查修复）：精确解析 -d 输出中
  DT_NEEDED/RPATH/RUNPATH/SONAME 方括号内的值（兼容 GNU "(NEEDED)" 与
  llvm " NEEDED" 两种格式），[libxxx.so] 允许、[/绝对路径/libxxx.so] 或
  值含宿主路径（/storage/、/home/、/data/service、/devcloud）必须失败，
  条目行缺完整 [value] 记 parse_fail；readelf/grep 退出码异常（非 0/1）
  一律 fail closed。旧实现 `strstr(buf, "]: /")` 永远匹配不到（readelf
  实际格式是 "[libgmp.so.10]"，不产生 "]: /" 序列）——已删。
- 交叉构建时 conanrun 拿不到 hnp bash：测试运行用 /bin/sh -c（POSIX 足够）。
- CI worker 与本机工具链布局不同（profile 写死 hnp 路径）：本地复现用
  ~/.conan2/profiles/ohos-aarch64-local（bash/clang 在 ~/usr/local/bin）；
  recipe 侧 CONFIG_SHELL 覆盖 + 命令行前缀赋值双保险（E551）。

- **MPFI 不使用硬件 fenv**：grep 全源码无 fenv.h/fegetround/fesetround；
  舍入全部经 MPFR 软件舍入（MPFR_RNDD/RNDU 显式传参），mpfi-impl.h 定义
  `MPFI_RNDD/RNDU = GMP_RNDD/RNDU`。因此 musl 与 glibc 的 fenv 差异
  对 MPFI 无影响；test_ohos.c 仍验证「调用前后 fenv 模式保持」契约。
- **无消费者须继承的行为宏**：mpfi.h 无 #ifdef 分支依赖外部定义的宏
  （grep 无 MPFI_* 行为开关）；静态/共享通过通常的 mpfi_DLL 宏
  仅影响导出注记，消费者无需 -D。
- **编译器优化不破坏外舍**：MPFI 端点运算全部走 MPFR API
  （mpfr_add 等，多精度软件实现），不经硬件浮点指令，
  -ffast-math/-O3 不影响区间端点舍入方向；test_ohos.c 用
  非精确端点（0.1/0.2、1/3）端到端复验。
- **oracle 必须用包含性**：测试不用 double 相等断言，全部为
  「高精度（300 位）真值 ∈ 区间」。
