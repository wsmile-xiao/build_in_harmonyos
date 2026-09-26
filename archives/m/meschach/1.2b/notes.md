# meschach 1.2b 适配笔记

## 编译环境
- 构建系统: autotools（autoconf 2.13 时代手写 configure + makefile.in，无 automake/libtool）
- 编译日期: 2026-09-24
- 编译器: clang 15.0.4 / aarch64-unknown-linux-ohos（`tools.build:compiler_executables` conf 注入绝对路径 CC）
- 状态: built

## 编译步骤

**必须 in-source**（上游 configure 的机 epsilon 探针 `$CC -o macheps dmacheps.c` 不带 $srcdir，
out-of-source 直接 "no such file" → `D_MACHEPS`/`M_MAX_INT` 生成空宏破坏 machine.h；
实测证据 `$TASK_DIR/oos-build/cfg.log`）。同型先例 mpgtx（手驱 configure+make 于 source_folder）。

```bash
CC=<绝对路径 clang> CFLAGS='-O3 -pipe -DNDEBUG' ./configure --with-all
make -j1 CFLAGS='-O3 -pipe -DNDEBUG'     # makefile.in 的 CFLAGS=-O 是字面量非 @CFLAGS@，
                                         # configure 期 CFLAGS 传不进 ⇒ make 调用行必须再钉一次
```

- `--with-all` **必须**：`all` 目标无条件编译 part3/zpart 对象（makefile.in:68），
  而 `TYPE_SPMAT` 等守卫宏只在 `SPARSE`/`COMPLEX` 下定义（meminfo.h:55,58），
  二者都由 `AC_WITH(all,…)` 提供（configure.in:66-67）。缺则 `sparse.c` 报
  `use of undeclared identifier 'TYPE_SPMAT'` ×20（证据 `w0/w0-compile-probe.txt:30-56`）。
  **Debian rules 同口径**：`./configure --prefix=/usr … --with-all`。
- 产物：`meschach.a`（ar 归档，无 lib 前缀）；`package()` 重命名为 `libmeschach.a`。
- 上游 makefile **无 install 目标**（Debian 同为手工 cp，`override_dh_auto_install`），
  配方按 debian/rules 头文件清单（12 个）手工落 `include/meschach/` 子目录
  （Debian `/usr/include/meschach` 同口径；matrix.h/err.h 为极通用名，平铺会污染消费者 include 面；
  自有头互引全为引号形式，子目录内可正确解析）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | clang15 报 `zmatrix.h:41:10: error: expected ';' after struct` | configure 探测到系统 `<complex.h>` 后 `machine.h` include 它；C99 `complex` 是宏，把 meschach 自带 `typedef struct{…} complex` 展开坏 | **configure 侧移除 complex.h 探针**（补丁 0001/0002）。**Debian 官方同判同修**：`meschach_1.2b-13.configure.diff:4602-4605` 注释原文「No no no no no! Meschach does NOT support complex.h … Drew Parsons, 2001」，`##AC_HEADER_CHECK(complex.h,…)`。取舍依据：符号面核对显示 `typedef complex` 单点定义于 zmatrix.h:41、使用面 23 文件、`<complex.h>` 唯一 include 点 machine.h:122 且有 `#ifdef HAVE_COMPLEX_H` 守卫 ⇒ configure 侧断源后整链规避、**zmatrix.h 及 23 文件零改动**（反向改 typedef 面 delta 大且偏离 Debian 修法）。复现：`printf '#include <complex.h>\n#include "zmatrix.h"\n' | clang -fsyntax-only -I <src> -` → rc=1 命中；去掉 complex.h → rc=0 |
| 2 | 默认 configure 构建必炸 `TYPE_SPMAT` 未声明 | `all` 无条件编 part3/zpart，而守卫宏只由 `--with-all` 定义 | 配方固定 `./configure --with-all`（Debian rules 同口径）；证据 `w0/w0-compile-probe.txt` |
| 3 | configure 探针 `maxint: inaccessible or not found`×4 | `AC_DEFINE_UNQUOTED(D_MACHEPS,\`macheps\`)` 反引号执行无 `./` 前缀，设备 PATH 不含 cwd ⇒ 探针不执行、生成空宏 | 补丁 0001/0002 改为 `` `./macheps` ``、`` `./maxint` ``（裸命令名 §一.14 同族）；修复后 machine.h `D_MACHEPS 2.22045e-16` |
| 4 | out-of-source configure 生成空 `D_MACHEPS` | epsilon 探针编译不带 $srcdir | 必须 in-source（见「编译步骤」）；证据 `oos-build/cfg.log`、`oos-build/machine.h:182` |
| 5 | clang15 大量 `-Wdeprecated-non-prototype`/`-Wimplicit-int` 告警 | 1990 年代 K&R C（函数无原型、隐式 int） | **如实记录**：告警非错误、非 -Werror，构建不受阻（77 warnings / 0 errors 形态）；不改上游 K&R 源码 |

## 源码修改

- `patches/0001-configure.patch`：移除 configure 的 complex.h 探针块（引 Debian Drew Parsons 2001 同判注释）+ epsilon 探针加 `./` 前缀。
- `patches/0002-configure.in.patch`：configure.in 同步两处修复（保持再生成一致性；`##AC_HEADER_CHECK(complex.h,…)` 与 Debian 同款）。
- 两补丁对原树 `patch -p1 --dry-run` 实测 APPLIES_OK；conandata.yml 已登记（strip: 1）。

## 依赖版本

- 运行/编译依赖：仅系统 `libm`（configure 唯一 `-l` 项 `LIBS="$LIBS -lm"`；全树 include 零第三方头）。无 Conan 前置依赖。

## 验证结果

```bash
# 上游测试面：7 个 torture 套件（makefile.in:184 alltorture），沙箱 HOME 下运行
# 判据 = 上游自身 Error 行计数（0 判 PASS）；rc 因 void main() UB 不作判据（已实证）
# 读数：套件 7 实跑 7 PASS 7 FAIL 0 SKIP 0 NOT_RUN 0；# Testing 测试段合计 99；Error 行总计 0
# 消费面：test_package/meschach_test 6 断言 6/6（稠密乘/转置/矩阵向量乘/向量加）
```

（详细四口径与证据路径见本包 `reports/test-report.md`；复现与取舍证据在
`$TASK_DIR/w0/`、`$TASK_DIR/tests/`。）

## 注意事项

- **`shared`/`fPIC` 选项为纯 package_id 声明（xplc/a52dec 同款）**：conan 2.29 对
  `package_type="library"` 硬校必须声明 `shared`（G2 第 1 轮 dependency graph 阶段
  9s 快证实测 `Package type is 'library', but no 'shared' option declared`）。
  上游 makefile 无 shared/static 开关（仅 ar 产 `meschach.a`）⇒ 本包**无 shared 构建路径**，
  选项不改变构建与交付、恒产静态单态、仅参与 package_id；配方**不向 configure 注
  `--enable-shared` 旗**（老 configure 未必认，presage 坑），CFLAGS 恒钉
  `-O3 -pipe -DNDEBUG`，fPIC 同理不接旗。默认 `shared=False, fPIC=True`。
- **配方自检三面缺一不可**（本轮教训，feedback 已记）：静态自检（py_compile/YAML 回读/
  正则编译）∪ 官方 PF 函数模拟 ∪ **`conan export` + `conan graph info` 双 rc=0**
  ——graph info 是 conan 侧硬校（shared 选项、conandata 解析等）唯一预跑面，
  PF 模拟覆盖不到。
- **源 URL 选 archive.ubuntu.com**：`deb.debian.org` 命中 PF7 `_PF7_DEBIAN_HOSTS`（A 类不可豁免，
  `--no-preflight` 按 §2 只许 PF0/PF8/PF9）；Ubuntu 池文件与 deb.debian.org/qlu 镜像/官方 .dsc
  三面 sha256 全等 `2b153bfd…5a050`（W0 三面锚定 + 本机第四面实测 200/220166B/MATCH），
  主机 PF7 名单外（mksh 反馈先例判「闸外 ✓」；pccts/calcurse 等 8 个在仓先例 CI 绿）。
- 纯静态库、无可执行产物（torture 为测试物不入库）⇒ 无 `commands.json`（PF8 R38：库误加即拦）。
- 软件级 `README.md` 为新包必填（finalize 校验）⇒ 触发 PF9 4 段路径**已知误报**（backlog#71），
  建 PR 时按 §2 用 `--no-preflight` + `--preflight-note` + 正文「预检豁免说明」留痕。
- K&R 告警清单见「问题 #5」，不得写成错误，也不得为消告警改上游源码。
---

**编译结束**: 2026-09-24 05:28
**最终状态**: built
