# tclap 1.2.5 适配笔记

## 编译环境
- 构建系统: autotools（上游 git 树无 `configure`，只有 `configure.ac`/`Makefile.am`）
- 编译日期: 2026-09-26
- 编译器: clang/clang++ 15.0.4（`aarch64-unknown-linux-ohos`，取自 conan conf `tools.build:compiler_executables`）
- 状态: built
- 交付形态: **header-only**（`package_type=header-library`，`implements=["auto_header_only_mode"]`，无 `lib/` 产物）

## 编译步骤

配方 `build()`（`conan create` 内执行，与设备手工验证同口径）：

```bash
# 1) 源码复制到 build 目录（source 目录只读；autoreconf 会写文件）
# 2) 上游 git 树没有 configure → 生成
autoreconf -fi
# 3) HMDFS 适配：生成的 configure 里 `umask 077` → `umask 022`（见问题 2）
# 4) configure（CC/CXX 从 conan conf 取，R33 不读环境变量）
./configure CC="clang" CXX="clang++"
# 5) make：编译 examples/ 的 30 个程序 + tests/test_wrapper（= header 的真实编译面）
make -j4
# 6) 上游 91 项测试
TMPDIR=<build>/tmp make check LOG_COMPILER=/bin/sh
# 7) 按 tests/*.sh.log 统计 PASS/FAIL 并与候选数法清点的 N 对账，不符即抛异常
```

设备手工同口径验证（沙箱 HOME，独立树 `$TASK_DIR/native`）：

```bash
autoreconf -fi && sed -i 's/umask 077/umask 022/g' configure
CC=$(command -v clang) CXX=$(command -v clang++) ./configure --prefix=/usr/local
make -j4
TMPDIR=$TASK_DIR/tmpdir make check LOG_COMPILER=/bin/sh
# → # TOTAL: 91 / # PASS: 91 / # FAIL: 0 / # SKIP: 0 / # ERROR: 0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make check` 首跑 91 项中 80 项 FAIL，日志逐条 `sh: can't create /tmp/tmpnam_XXXXXX: Read-only file system` | `tests/test_wrapper.cpp` 用 `std::tmpnam(NULL)` 生成临时文件，**恒返回 `/tmp/...`**（不看 `TMPDIR`），而 HMDFS 的 `/tmp` 只读 ⇒ 重定向失败、`f_tmp.fail()` 返回 2，**比较从未执行**（设备事实 §一.1 同族的"测量装置失效"） | **补丁 0001**：改为在 `$TMPDIR`（缺省当前目录）`mkstemp` 生成临时文件；比对逻辑、用例数、参考输出一字不动。修后 91/91 PASS |
| 2 | `./configure` 末尾 `config.status[740]: can't create ./confXXXXXX/subs1.awk: Permission denied` → `config.status: error: could not setup config files machinery`（rc=1/20） | autoconf 生成的 config.status 用 `umask 077 && mktemp -d ./confXXXXXX` 建临时目录；HMDFS 把目录属主映射成共享属主后 0700 目录对当前进程不可写（知识 **E011/E114** 已命中该签名） | `configure` 是 `autoreconf` 的**生成物**（不入库），在 `build()` 内生成后就地 `umask 077` → `umask 022`（命中数<1 即抛异常，不静默跳过）；不做成补丁 |
| 3 | `tests/test88.sh`…`test91.sh` shebang 是 `#!/bin/bash`，OHOS 无 `/bin/bash`（设备事实 §一.16）⇒ 直接执行报 `No such file or directory` | 上游 2005 年脚本假设 GNU 环境；4 个脚本体本身无 bash 特性 | `make check LOG_COMPILER=/bin/sh` 统一交给 POSIX sh 执行（automake 并行测试驱动的 `LOG_COMPILE` 前缀），**脚本一字不改** |
| 4 | 采信轮 R1：`autoreconf` 死于 `Perl_my_cxt_init: symbol not found`；R2 换 PATH 前置后 `aclocal` 同错 | ①OHOS profile 把 `/data/service/hnp/bin` 排在 PATH 最前，HNP 的 `autoreconf` 遮蔽 conan 工具；②`tool_requires autoconf/2.72` 连带 `perl/5.42.2`，其 `PERL5LIB`（`aarch64-linux-thread-multi` 的 XS）被 HNP 的**非线程** perl 5.42.0 读到，加载 `Cwd.so` 符号失配；`.aclocal-real` shebang 写死 `#!/data/service/hnp/bin/perl`，PATH 前置改不掉解释器 | 只保留 `tool_requires("automake/1.18")`（HNP 缺的正是它）；每条命令 `PATH="<conan bin>:…"` 前置 + `PERL5LIB="<automake share>"` 收窄——HNP perl 用自己的核心 XS、`Automake::*` 走纯 perl 模块目录 |

## 源码修改

- `patches/0001-tests-test_wrapper.cpp.patch`（`patch_type: platform`，仅测试夹具）：
  `tests/test_wrapper.cpp` 的临时文件生成由 `std::tmpnam(NULL)` 改为 `makeTempName()`——
  `$TMPDIR`（缺省 `.`）+ `mkstemp`；只动临时文件路径，**不动比较逻辑、不动 `tests/` 用例与参考输出**。
  平台外（`/tmp` 可写）行为等价。
- `build()` 内对**生成物** `configure` 的 `umask 077 → 022`（不入提交面）。

## 依赖版本

- **运行依赖：0**（纯头文件库，`requirements()` 为空；`conan list tclap/* -r=ohpcd` 与配方 requires 双零）
- **构建工具**：`tool_requires("automake/1.18")`（ohpcd 在档，`conan download --only-recipe` 实查通过）；
  `autoreconf/autoconf/autoheader/autom4te/m4/perl` 取设备与 CI worker 同源的 HNP
  （`/data/service/hnp/bin`，R36/PF4 面只有 automake 一条）。
  **不引 `tool_requires("autoconf/2.72")`**：它连带 `perl/5.42.2`，其 buildenv 的
  `PERL5LIB`（threaded XS 目录）会被 HNP 的非线程 perl 读到——`.aclocal-real` 的
  shebang 写死 `#!/data/service/hnp/bin/perl`，PATH 前置也改不了它，于是
  `Can't load …/auto/Cwd/Cwd.so: Perl_my_cxt_init: symbol not found`（采信轮 R1/R2 实测）。
  处方：`PERL5LIB` 只留 automake 自己的 `share/automake-1.18`（`Automake::*` 纯 perl）。

## 验证结果

```bash
# 源码 sha256 三路核对（W0-1）
git ls-remote --tags https://github.com/mirror/tclap.git | grep v1.2.5
#   58c5c8ef24111072fc21fb723f8ab45d23395809  refs/tags/v1.2.5
curl -sSL -o tclap-v1.2.5.tar.gz https://github.com/mirror/tclap/archive/refs/tags/v1.2.5.tar.gz
sha256sum tclap-v1.2.5.tar.gz
#   7e87d13734076fa4f626f6144ce9a02717198b3f054341a6886e2107b048b235
#   = CCI recipes/tclap/all/conandata.yml 的 "1.2.5" 条目，逐字一致

# 上游测试（设备、沙箱 HOME、独立树）
TMPDIR=$TASK_DIR/tmpdir make check LOG_COMPILER=/bin/sh
#   # TOTAL: 91   # PASS: 91   # FAIL: 0   # SKIP: 0   # ERROR: 0
```

- W0-3 平台可移植性：`altivec.h / xmmintrin / immintrin / 3dnow / register_printf_ / printf.h / _mm_ / __builtin_ia32 / arm_neon` **九类 grep 全 0 命中**（0 文件），无 ISA/printf 钩子风险。
- 采信轮（`tools/conan_verify_round.sh`）读数见同目录 `reports/`。

## 注意事项

- **header-only 交付形态**：`conan-verify` 的 G4/L2/L4/L5 对无 `bin/`、无 `lib/` 的包走"跳过"分支
  （设备事实 §二.17）⇒ 这些行的 `✅` 不作数，需人工补测写 `reports/conan-verify-supplement.md`
  （G4 交付清单↔`package_info()`、L2 消费者真跑、L4 静态库核对不适用、L5 交付物 sha256）。
- 上游测试 N=91（候选数法三口径同值）；`test_package` 的 11 条消费者断言**不进上游分母**。
- 上游 91 个用例中 `test8`/`test40`/`test70`/`test85` 等 11 个把 `-h`/`--version`/`--help`
  作为子命令参数，`test_wrapper` 自身的 TCLAP 解析会先吃掉该旗标并 exit 0——这是**上游既有行为**
  （各平台一致），本任务不改判据，按 `make check` 原语义计数。
