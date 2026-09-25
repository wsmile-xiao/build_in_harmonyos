# qsopt-ex 2.5.10.3 适配笔记

## 编译环境
- 构建系统: autotools（源码树只有 configure.ac，build() 内 autoreconf 自举）
- 编译日期: 2026-09-23
- 编译器: clang 15.0.4 / aarch64-unknown-linux-ohos（OHOS SDK 26.0.0.18）
- 状态: built

## 编译步骤

1. `autoreconf --force --install`（与上游 `bootstrap` 等价）。tool_requires 提供
   `aclocal/1.18`、`automake`、`libtoolize`（`ACLOCAL`/`AUTOMAKE`/`LIBTOOLIZE`/
   `ACLOCAL_PATH` 由其 package_info 注入）；autoconf/autoreconf 家族用 CI 与
   设备 `/data/service/hnp/bin` 自带（**刻意不** `tool_requires autoconf/2.72`，
   见下表 #3）。
2. 配方对自举后的 `configure` 施加 HMDFS 临时目录修正（见下表 #2），随后
   `./configure --build=aarch64-unknown-linux-gnu --disable-shared --enable-static`
   （gmp 头/库经 conan 依赖注入 CPPFLAGS/LDFLAGS，`AC_CHECK_LIB gmp/__gmpz_init`
   自动探测通过）。
3. `make -j1` 构建 `libqsopt_ex.a`、`esolver`、`tests/test_qs`、`tests/eg_sloan`。
4. `make check` 跑上游唯一注册测试 `tests/test_qs`（TAP plan `1..8`），
   `LOG_DRIVER` 显式换 POSIX `/bin/sh` 执行上游 `tap-driver.sh`（见下表 #3）。
5. `make install`：`bin/esolver` + `include/qsopt_ex/*.h`（97 个公开头）+
   `lib/libqsopt_ex.a`；`package()` 删除 libtool `*.la`（内含 gmp 构建期绝对路径）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type` | `config.guess` 不认识 `UNAME_SYSTEM=HarmonyOS / HongMeng Kernel`（正式条目 E160 同族） | 配方 `generate()` 追加 `--build=aarch64-unknown-linux-gnu`（a52dec/acct 先例同款），不补丁 config.guess |
| 2 | `config.status: .../subs1.awk: Permission denied` | autoconf 2.73 的 `tmp=\`(umask 077 && mktemp -d ...)\`` 走 `mktemp -d`：mktemp 强制 chmod 700，HMDFS 落盘 `2700` 且属主被映射后 euid 不可写；而 autoconf 的 `mkdir` 回退分支落盘 `2771`（HMDFS 强制保留组位）可写 | **autoreconf 之后**把该 mktemp 分支字面替换为强制失败，令 config.status 落回 mkdir 回退（E114 正式条目；abiword `_drop_umask_077` / a52dec 补丁 0002 / acct mktemp 包装同族） |
| 3 | `tool_requires autoconf/2.72` 后 autoreconf 崩：`Perl_my_cxt_init: symbol not found` | conan perl 5.42.2 的 XS 模块与 HNP 自带 perl 5.42.0 ABI 不兼容，而 PATH 上的 autoreconf 是 HNP 版（工作区 §一.23「毒丸」，comptty 先例已记） | 不 tool_requires autoconf；autoconf 家族用 HNP 自带，只 tool_requires automake+libtool（二者不拉 perl 解释器，PERL5LIB 只含 automake 纯 perl 模块，无 ABI 面） |
| 4 | `make check` 报 `sh: >&3 : bad file descriptor`、`missing test plan`、`tests/test_qs.log` **0 字节**、`# TOTAL: 2 / ERROR: 2`，而同二进制直跑 TAP 8/8 全过 | 上游 `tap-driver.sh` 在「管道子 shell + 外层组重定向 `3>"$log_file"`」下，本机/CI 的 bash 5.3 对 fd3 的 `dup2(2>&3)` 判定失效（实测 bash 报 `3: Bad file descriptor`，toybox `/bin/sh` 同结构正常）——典型「非 0 产物假绿/假红」面（G11 同族） | `make check 'LOG_DRIVER=env AM_TAP_AWK=$(AWK) /bin/sh $(top_srcdir)/tap-driver.sh'` 强制 POSIX sh 执行 driver；修后 `# TOTAL: 8 / PASS: 8 / ERROR: 0`，log 744B。正式草稿 E675 |
| 5 | esolver 无长选项：`esolver --version`/`--help` 返回 1 | 上游 `ILLutil_bix_getopt` 只认单横线选项，未知选项走 `usage(); return 1`；平台冒烟门 L2 要求 rc=0 | 补丁 0001 在 `parseargs` 入口显式处理 `--version`（复用 `-v` 的 `mpq_QSversion` 打印）与 `--help`（usage），均 `exit(EXIT_SUCCESS)` |
| 6 | MPS 样例首版 `rc=0` 但 `Value = 0`（VARS 为空） | MPS 标准语义默认 **minimize**，且 QSopt_ex 只认 CPLEX `OBJSENSE` 扩展切换 MAX；无 OBJSENSE 时最优解落在原点——`rc=0 + 非空产物 + 错误最优值` 的高危假绿形态 | 样例补 `OBJSENSE` / `  MAX` 段后 `Value = 14`、解 (1,4)；测试断言带**预期最优值标记**而非仅 rc/非空 |
| 7 | 消费者链接报 `undefined symbol: gzopen/gzwrite/...`（静态库隐式依赖系统 zlib） | configure 的 `AC_CHECK_LIB(z/bz2)` 探测随环境漂移（原生探索命中 harmonybrew/SDK 的 zlib → `HAVE_LIBZ=1` → `eg_io.c` 编入 `gz*` 调用），静态库把可选依赖泄漏给下游 | 按 W0 可选依赖口径**缺省禁用**：configure 传 `ac_cv_lib_z_gzopen=no`、`ac_cv_lib_bz2_BZ2_bzopen=no`（调用点全部在 `#ifdef HAVE_LIBZ/HAVE_LIBBZ2` 守卫内，未启用时打 "no zlib support" 日志返回）→ 库与消费者零隐式压缩依赖，设备/CI 行为一致 |
| 8 | 采信轮 G2 首败：`checking for __gmpz_init in -lgmp... no` → `GNU MP not found` | 只用了 `AutotoolsToolchain`（工具链旗标），**没有 `AutotoolsDeps`**——requires 的 `-I/-L/-l` 不会进 `CPPFLAGS/LDFLAGS/LIBS`，configure 的依赖探测自然找不到 gmp | `generate()` 里先 `AutotoolsDeps(self).generate()` 再 `tc.generate()`（有 requires 的 autotools 配方必配；无依赖的先例配方看不出这个坑） |
| 9 | 采信轮 G2 次败：链接 `undefined symbol: ILL_IFTRACE2`（百余处引用，仅 Release 出现） | **上游 `qsopt_ex/trace.h` 笔误**：`#ifndef NDEBUG` 的 `#else` 分支写了两行重复的 `ILL_IFTRACE`、漏掉 `ILL_IFTRACE2`；conan Release（`-DNDEBUG`）走该分支 ⇒ 宏未定义退化为外部符号（原生探索未加 `-DNDEBUG` 故不复现） | 补丁 `0002-trace-h-define-ILL_IFTRACE2-under-NDEBUG.patch`：把重复行改为 `#define ILL_IFTRACE2 if (0) QSlog`（最小 diff，随上游「优化器消除」意图） |

## 源码修改

- `patches/0001-esolver-long-options-for-smoke-test.patch`：`esolver/esolver.c`
  `parseargs()` 入口增加 `--version` / `--help` 两个长选项处理（均 exit 0）。
  仅平台冒烟兼容，不改求解逻辑。
- `patches/0002-trace-h-define-ILL_IFTRACE2-under-NDEBUG.patch`：`qsopt_ex/trace.h`
  的 NDEBUG 分支补回漏定义的 `ILL_IFTRACE2`（修正重复的 `ILL_IFTRACE` 行），
  修复 Release `-DNDEBUG` 下的链接错误（上游笔误，最小 diff）。
- HMDFS config.status 临时目录修正发生在 `configure`（自举产物）上，不进补丁面
  （上游源码树不含 configure，补丁无法落点），处置写在 `conanfile.py`
  `_fix_conf_tmpdir()` 内并附根因注释。

## 依赖版本

- 运行/链接: `gmp/6.3.0`（硬依赖；公开头 `QSopt_ex.h` 直接 `#include <gmp.h>`，
  故 requires 带 `transitive_headers=True, transitive_libs=True`）
- 构建工具（tool_requires）: `automake/1.18`、`libtool/2.5.4`；
  autoconf 家族 = CI/设备 `/data/service/hnp/bin` 自带 2.73
- 可选依赖 `zlib`/`bzip2`（`.sol.gz`/`.sol.bz2` 压缩写盘）按 W0 可选依赖口径
  **缺省禁用**（`ac_cv_lib_z_gzopen=no`、`ac_cv_lib_bz2_BZ2_bzopen=no`），不引入
  额外 Conan 依赖；对应调用点全在 `#ifdef` 守卫内，运行期仅对该压缩格式打
  "no zlib support" 日志

## 验证结果

（见 `reports/test-report.md`；采信轮 `reports/conan-verify-report.md`）

## 注意事项

- **已知限制**：`esolver -O out.sol.gz` / `.bz2` 压缩输出按可选依赖口径未启用
  （纯文本 `.sol` 输出与求解功能完整）。
- 上游测试极薄：**全上游仅1个注册测试 / TAP 8 条断言**（`TEST_COUNT=8`），
  源码树零夹具、零 `.map` 样例；`tests/{ftest.c,solver.c,eg_lpnum_ex.c}` 未接入
  Makefile（不计入 N）。
- 因此另有自备样例 `.map`（LP/MPS 标准格式，sha256 锚定于任务私有
  `sources/fixtures/`）驱动的鸿蒙特有求解测试，产物断言带预期最优值标记。
