# coinor-cbc 2.10.13 适配笔记

## 编译环境
- 构建系统: autotools（上游 release tarball 自带预生成 configure；Cbc/ 子包为新式
  AC_COIN_CHECK_PACKAGE + pkg-config 模块名口径）
- 编译日期: 2026-09-21
- 编译器: /data/service/hnp/bin/clang（OHOS clang 15, aarch64）
- 状态: built

## W0 依赖预检结论（生死关，2026-09-21 实核）
- 上游 release tag `releases/2.10.13` tarball **不捆绑依赖**（`.coin-or/Dependencies`
  声明 CoinUtils/Osi/Clp/Cgl 四个硬依赖 + 可选 ThirdParty-ASL/Glpk/Metis/Mumps 与
  Data-Sample/miplib3/Netlib）。
- 四个硬依赖在 ohpcd **全部已发布**（`conan install --build=never` 实测二进制命中，
  非 conan list 口径，R35 合规）：
  - coinutils/2.11.13（include/coin + libCoinUtils.a + 原生 coinutils.pc）
  - coin-or/0.108.12（= Osi；include/coin + libOsi.a + libOsiCommonTests.a + osi.pc/osi-unittests.pc）
  - clp/1.17.10（include/coin + libClp.a/libClpSolver.a/libOsiClp.a + clp.pc/osi-clp.pc）
  - cgl/0.60.10.1（include/coin + libCgl.a + cgl.pc）
  - zlib/1.3.1（coinutils 的 -lz 闭包）
- 版本可得性实核：Cbc 官方 GitHub tag 归档
  https://github.com/coin-or/Cbc/archive/refs/tags/releases/2.10.13.tar.gz
  sha256=62fde44dcf6f3d05c5cd291d7435cdd1b7e8acd3c78ec481dd39fe49cbc40399（实测）。

## 集成口径（为什么是 flags 模式）
1. 子包 `Cbc/configure` 用 `AC_COIN_CHECK_PACKAGE(CoinDepend,[cgl osi coinutils])` 等
   pkg-config 模块名；但已发布依赖包的 .pc 在构建时把 `prefix=/` 固化，`libdir=/lib`
   与 `Libs:` 内嵌构建机绝对路径，对本机 conan 包目录不可用 → 不能走 pkg-config。
2. configure 的 `--with-<pkg>-lib / --with-<pkg>-incdir` flags 分支直接置
   `coin_has_*=yes` 并跳过 pkg-config（configure 脚本 20840–20935 行段实测核对）。
3. incdir 只接受单目录，而依赖头分居各包 include/coin → generate() 里合并到
   generators 目录单一 staging（`coin-include/`），三个 incdir 共用。
4. 闭包链接串按「依赖方在前」重复展开（同上游 cgl.pc 口径），**用直连 .a 路径而非
   `-l<name>`**（依赖包 .la 固化 `libdir='//'`，`-l` 形式会让 libtool 解析出
   `//lib/libX.la` 报 not a valid libtool archive，见问题表 #7）：
   - CoinDepend: `<cgl>/lib/libCgl.a <osi>/lib/libOsi.a <coinutils>/lib/libCoinUtils.a <zlib>/lib/libz.a -lm`
   - Clp: `<clp>/lib/libOsiClp.a <clp>/lib/libClpSolver.a <clp>/lib/libClp.a` + CoinDepend 闭包
   - OsiTests: `<osi>/lib/libOsiCommonTests.a` + CoinDepend 闭包
5. 直接驱动子包 `<src>/Cbc/configure`（顶层 configure 只做子包编排，跳过少一层
   HMDFS 脆弱的 autoconf 2.59 config.status）。
6. 可选外部求解器/数据全部显式 `--without-*` 关闭（dylp/vol/cpx/glpk/grb/highs/msk/
   spx/xpr/asl/mumps/nauty/netlib）；`--with-cbc-generic` 打开 cbc-generic 驱动。

## 编译步骤

配方 build() 内固定序（全部在源码树 Cbc/ 子目录 in-source 执行）：

```bash
# 1. shebang/config.guess HMDFS 修复（configure 等 7 个脚本 × 根与 Cbc/ 两层）
# 2. configure（flags 模式注入依赖；编译 flags 亦显式钉死，不继承环境泄漏值——见问题表 #8）
CC=clang CXX=clang++ CFLAGS='-O3 -pipe -DNDEBUG' CXXFLAGS='-O3 -pipe -DNDEBUG' \
  ./configure --prefix=/ \
  --build=aarch64-unknown-linux-musl \
  --enable-static --disable-shared --disable-dependency-tracking \
  --with-coindepend-incdir=<合并头 staging> \
  --with-coindepend-lib='<cgl>/lib/libCgl.a <osi>/lib/libOsi.a <coinutils>/lib/libCoinUtils.a <zlib>/lib/libz.a -lm' \
  --with-clp-incdir=<合并头 staging> \
  --with-clp-lib='<clp>/lib/libOsiClp.a <clp>/lib/libClpSolver.a <clp>/lib/libClp.a <同前闭包>' \
  --with-ositests-incdir=<合并头 staging> \
  --with-ositests-lib='<osi>/lib/libOsiCommonTests.a <同前闭包>' \
  --with-sample-datadir=<Data-Sample> \
  --with-miplib3-datadir=<Data-miplib3> \
  --with-cbc-generic \
  --without-dylp --without-vol --without-cpx --without-glpk --without-grb \
  --without-highs --without-msk --without-spx --without-xpr \
  --without-asl --without-mumps --without-nauty --without-netlib
# 3. config.status 的 HMDFS 修复（umask 077→022、mktemp→conftmp）后重跑
# 4. make -j1（ MAKEFLAGS='' ）
# 5. .lo 修复（src、src/OsiCbc、test）
# 6. 5 个测试 ELF 自签后 make test
# 7. make install DESTDIR=<包目录>（.lo 再修一次）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | .pc 的 libdir=/lib 固化 + Libs 内嵌构建机绝对路径 | 已发布依赖包 prefix=/ 固化 | 弃用 pkg-config，改 configure flags 模式显式注入 |
| 2 | --with-*-incdir 只接受单目录，依赖头分居各包 include/coin | COIN m4 宏形态 | generate() 合并四包头到单一 staging |
| 3 | 脚本 shebang /bin/bash、/bin/sh（设备无 /bin/bash，§一.16） | 上游为桌面环境编写 | sed 改写 7 个脚本首行（CONFIG_SHELL/OHOS_SHELL） |
| 4 | config.status umask 077 + mktemp ./confstatXXXXXX 落盘 2700 不可写（§一.10） | HMDFS 目录模式落盘行为 | sed 改 022 + ./conftmp 后重跑 config.status |
| 5 | libtool .lo 文件被 HMDFS 截断 | HMDFS 对小文件并发写 | make 后对三目录 .lo 修复（带 [ -e ] 守卫） |
| 6 | TMPDIR 被 HiShell 注入成 $HOME（§一.12） | 设备 shell 环境 | build() 强制 TMPDIR/TMP 指向可写目录 |
| 7 | libtool 链接 libCbc.la 报 `//lib/libClp.la is not a valid libtool archive` | 依赖包 .la 固化 libdir='//'（prefix=/）；`-l<name>` 触发 libtool 读 .la 并按其 libdir 解析 | 闭包串改直连 .a 路径（`<pkg>/lib/libX.a`，同上游 cgl.pc 写法），libtool 不再解析 .la |
| 8 | 首轮 CI 红：`make: *** [Makefile:988: test] Error 2` ← `make[1]: *** [Makefile:824: ositests] Segmentation fault (core dumped)`（CI build#56630） | CI worker 进程环境泄漏 `CFLAGS/CXXFLAGS='-fPIC -O2'`（**无 -DNDEBUG**；profile 与 ci/ 脚本均不设置），配方未钉编译 flags ⇒ CI 构建偏离设备/W3 已验证配置；上游 `OsiCbcSolverInterfaceTest.cpp:122` 的 `if (!OsiCbcHasNDEBUG())`（`#ifdef NDEBUG` 编译期常量）分支只在无 -DNDEBUG 时执行，CI 执行该异常测试段后段错误（本地以 CI 同款 flags 逐字复现同款崩溃） | build() 在 configure 调用处显式钉死 `CFLAGS/CXXFLAGS='-O3 -pipe -DNDEBUG'`（R33 同款纪律、设备已验证基座值），CI/W3/设备三方同源；bot「编译失败/429」分类为误判，真错以 buildbot 日志原文为准 |

## 源码修改

无补丁（conandata patches: {}）。依赖注入与 HMDFS 修复全部在配方 build() 内完成，
不改动上游源码。

## 依赖版本

- coinutils/2.11.13
- coin-or/0.108.12（Osi）
- clp/1.17.10
- cgl/0.60.10.1
- zlib/1.3.1

（全部为 ohpcd 已发布二进制，`conan install --build=never` 实测命中；与 cgl/0.60.10.1
的钉版闭包完全一致，避免双版本图，R36。）

## 测试数据包（官方 coin-or-tools 源，R39）

- Data-Sample releases/1.2.13，sha256=cb4c3713b2a2510d0b6387c24a68c88ba5eff27e2c392429653b1bdef50f06c9
- Data-miplib3 releases/1.2.9，sha256=4e4aa82d70989b115542c8394384e5e43a16db0550df472fed8fb0d67111e5ec
- Data-Netlib：未引入（约 40MB，仅扩展 ositests 的 -testOsiSolverInterface 面，
  体积/时长代价大，如实申报）

## 上游测试清点（R51，口径 = Cbc/test/Makefile.am 的 make test 目标注册）

| 目标 | 激活条件 | 本包状态 |
|------|---------|---------|
| gamstests | 无条件 | 运行 |
| ositests | 无条件（-mpsDir 需 Sample） | 运行（含 Sample 数据面） |
| ctests | COIN_HAS_CLP | 运行 |
| test_cbc | COIN_HAS_CLP && COIN_HAS_SAMPLE（-unitTest 需 miplib3） | 运行 |
| test_cbc_generic | CBC_BUILD_CBC_GENERIC && COIN_HAS_SAMPLE | 运行 |
| （netlib 扩展面） | COIN_HAS_NETLIB | **未运行**（数据包未引入，如实申报） |

N = 5（注册目标数）；N′ 与逐目标结果见 reports/test-report.md 与设备日志转写。

## 验证结果（实测后回填）

```bash
# 见 reports/test-report.md（真实设备日志逐字转写）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/cbc | 5,134,848 B | 主求解器 CLI（自签后真跑验证） |
| bin/cbc-generic | 4,094,464 B | 通用驱动（--with-cbc-generic） |
| lib/libCbc.a | 398,491,168 B | 静态库（内含依赖闭包成员，见注意事项） |
| lib/libCbcSolver.a | 398,007,216 B | 静态库（同上） |
| lib/libOsiCbc.a | 396,382,226 B | 静态库（同上） |
| include/coin/ | 76 个头 | Cbc 公共头 + CbcConfig.h |

注意：三个 .a 因 libtool 对 LIBADD 中直连 .a 的吸收语义内嵌依赖闭包成员
（libOsiClp/libClp/libCgl/libOsi/libCoinUtils/libz），体积大但链接语义正确
（消费端 ld 按成员首遇去重）；与已发布同族包 cgl/0.60.10.1 的 libCgl.a 形态一致。

## 注意事项

- conandata.yml sources 含三个条目（主源 + 两个数据包），source() 按键显式 get，
  不用 `**conan_data["sources"]` 展开（多键会污染 get kwargs）。
- conandata 无源码补丁（patches: {}）：依赖注入与 HMDFS 修复全部在配方 build() 内，
  不改动上游源码，R3/R6 合规。
- commands.json：软件级声明 cbc/cbc-generic 命令行工具（R38）。
- 版本钉版一致性：cgl/0.60.10.1 上游配方钉 clp/1.17.10（非 1.17.11），本包与已发布
  闭包完全同钉版（R36）。
- OHOS 上构建产物运行前必须 binary-sign-tool 自签（加载器 EPERM）。
