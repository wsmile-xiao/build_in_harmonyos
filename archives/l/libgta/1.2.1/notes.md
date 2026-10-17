# libgta 1.2.1 适配笔记

## 编译环境
- 构建系统: autotools（manifest `build.system=autotools`；CMake 入口存在但**不注册 tests/**，上游测试面只在 autotools 入口，故双入口按 manifest 选 autotools）
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，profile `tools.build:compiler_executables` 注入）
- 状态: built

## 编译步骤

W0 预检（先于配方）：
- 版本可得性：官方下载面 `https://marlam.de/gta/releases/libgta-1.2.1.tar.xz` 实测 200、326520 B；本机 sha256 =
  `d445667e145f755f0bc34ac89b63a6bfdce1eea943f87ee7a3f23dc0dcede8b1`，与任务卡 CCI conandata 声明前缀 `d445667e…` 一致，
  且与 Phytium-Pi-OS `package/libgta/libgta.hash` 的逐字记录（同名文件同值）双源互证。上游 git 不可达
  （gitlab.com/marlam/gta 要凭证、marlam.de/git/gta 404），按「官方渠道存在该版本可构建发行物」判据以下载面实证放行。
- 硬依赖：`configure.ac` 的 zlib/bz2/lzma 只在已废弃 `--with-compression`（默认 `compression="no "`，configure.ac:73-77）下探测；
  `CMakeLists.txt` 无三方 find_package（仅文档可选 Doxygen）→ **默认构建零依赖**，无需 `conan list` 实查。
- 平台可移植性：`altivec/mmx/3dnow/immintrin/register_printf_*/printf.h` 全树 grep **0 命中**（止损先例 #14 三步判据第①步），
  无强制 ISA 路径与 glibc printf 钩子 → 直过。

探索树（`$WORKSPACE_ROOT/tmp/builds/libgta-1.2.1.work`，单树 in-source）：
1. `cp` 2026-05-17 版 config.guess/config.sub（含 `*:HarmonyOS:*:*` 分支）到 `build-aux/`；
2. `CC=/data/service/hnp/bin/clang CFLAGS="-O3 -pipe -DNDEBUG" ./configure --prefix=/storage/Users/currentUser/usr/local`
   —— 修复前 rc=1（config.guess 打回）、再修复前 rc=1（config.status 权限）；两处修复后 **rc=0**，
   `checking build system type... aarch64-unknown-linux-ohos`，`config.status: creating Makefile/config.h/...` 全量落地；
3. `make -j4` → rc=0（`src/.libs/libgta.so.1.0.0` + `libgta.a`）；
4. `make install DESTDIR=$TEST_PREFIX` → rc=0，安装树清点 **16 个文件**（3 头 + 4 库 + gta.pc + 8 个 doc 示例）；
5. `make check`（沙箱 `HOME=$TASK_DIR/test-home`）→ **TOTAL=6 PASS=5 SKIP=1 FAIL=0**；`check_PROGRAMS` 独有的 2 个 fuzz 驱动另以 100 轮种子迭代实测 **100/100**（`$TASK_DIR/logs/fuzz-drivers.log`）。声明 N 按候选数法取最大值 = 8（详见 `reports/test-report.md`）。

Conan 交付：`conanfile.py` 走 autotools 入口（`AutotoolsToolchain` 注入 `--prefix=/`，`autotools.install()` 补
`DESTDIR=<package_folder>` 落包）；shared 默认开（`--enable-shared --disable-static`）；`build()` 末 `-j1`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./configure` 在 `checking build system type` 直接 `./build-aux/config.guess: unable to guess system type` rc=1（2018-02-24 件） | 设备 `uname -s = HarmonyOS` 不在旧件分派表（E007 族，与 yapet 同） | 补丁 `0001/0002` 整文件升级到 2026-05-17 GNU config（savannah 官方件），`config.guess` 注入 `*:HarmonyOS:*:*` 分支输出 `aarch64-unknown-linux-ohos`，新 `config.sub` 实测认收该三元组；经 `refresh-patch --auto` 两面登记 |
| 2 | configure 尾部 `./config.status[1008]: can't create ./confbJLGCl/subs1.awk: Permission denied` + `config.status: error: could not setup config files machinery`（rc=1，Makefile/config.h 不落地） | autoconf 2.69 文件生成机制用 `(umask 077 && mktemp -d "./confXXXXXX")` 建暂存目录；**HMDFS 目录落盘 mode = 0777 & ~umask \| setgid、忽略请求 mode**（实测：同为 mktemp -d 请求 0700，umask 0002 落盘 `drwxrws--x` 可写、umask 077 落盘 `drwx--S---` 且 `touch` Permission denied）→ euid 非共享属主、组/其他无 w（E678/E114 族、device-facts §一.10） | 补丁 `0003` 对 **configure 源文件**两处归一：主路径 `tmp=./conftmp` + `(umask 022 && mkdir -p "$tmp")`、fallback 同改，残余 `umask 077` = 0。**关键点：autoconf 2.69 的 config.status 模板内嵌于 configure，生成的 config.status 自动继承修复，无需像 E678（autoreconf 族）那样对生成物做第二次 build() 期修复**；发布版 tarball 的 configure 是受跟踪源文件，故走 `patches/` 而非 build() 内 sed |
| 3 | 无 `cc`/`gcc`（`AC_PROG_CC` 候选表落空），`init-build` 环境检查报 `cc: 未找到` | 设备只有 HNP 前缀 clang（device-facts §一.7 同族：harmonybrew 有、worker PATH 无） | 探索期显式 `CC=/data/service/hnp/bin/clang`；Conan 阶段由 profile `tools.build:compiler_executables` → AutotoolsToolchain 注入 CC，CI 同源 |
| 4 | `make check` 中 `fuzztest.sh` 记 **SKIP** | 上游设计：`fuzztest.sh` 无参数调用固定 `exit 77`（脚本头原话 "Please consider to also run make fuzztest"），automake 记 SKIP；真实 fuzz 循环由 `make fuzztest` 驱动 | 计入声明 N=8 的 SKIP 并按上游设计归因（非环境失败）；`check_PROGRAMS` 独有的 `fuzztest-create`/`fuzztest-check` 以 100 轮种子迭代实测 **100/100 PASS**（`$TASK_DIR/logs/fuzz-drivers.log`，两驱动判 PASS）；另有 `./fuzztest.sh run` 跑满 60s 无失败标记（**补充证据，不计入分母**） |

## 源码修改

| 补丁 | 文件 | 内容 |
|------|------|------|
| `0001-build-aux-config.guess.patch` | `build-aux/config.guess` | 整文件 2018-02-24 → 2026-05-17 + `*:HarmonyOS:*:*` 分支输出 `aarch64-unknown-linux-ohos` |
| `0002-build-aux-config.sub.patch` | `build-aux/config.sub` | 整文件 → 2026-05-17（认收 `linux-ohos` 三元组） |
| `0003-configure.patch` | `configure` | config-files 暂存机制 `umask 077 && mktemp` → `umask 022 && mkdir -p`（主 + fallback 两处，E678 单点修法） |

三份补丁均过三关：NUL=0、`@@` hunk ≥1、对 `.orig` 真实 apply rc=0。

## 依赖版本

- 运行/构建依赖：**无**（manifest `build.dependencies: []`；压缩特性默认 off）。
- 工具链：clang 15.0.4 / GNU Make 4.4.1 / cmake 4.1.2（test_package 用）；均来自设备与 CI 同源 PATH，未新增 `tool_requires`。

## 验证结果

```bash
# 上游测试（沙箱 HOME，探索树 out-of-source）
HOME=$TASK_DIR/test-home make -C $WORKSPACE_ROOT/tmp/builds/libgta-1.2.1.work check
#   → # TOTAL: 6  # PASS: 5  # SKIP: 1  # FAIL: 0   （log: $TASK_DIR/logs/makecheck-sandbox.log）
# fuzz 驱动补测（check_PROGRAMS 独有 2 单元）
#   → fuzz-driver iterations: PASS=100 FAIL=0 (of 100)  （log: $TASK_DIR/logs/fuzz-drivers.log）
# 声明 N=8 = max(TESTS 6, check_PROGRAMS 7, 并集 8)；N′=8：PASS=7 SKIP=1 FAIL=0 NOT_RUN=0

# 消费者探针对安装树直连（test_package/test.c 同源）
clang -I<install>/include test.c -L<install>/lib -lgta && LD_LIBRARY_PATH=<install>/lib ./consumer_probe
#   → test_package: 20/20 assertions passed

# 采信轮（conan_verify_round.sh rc=0；干净轮标志 run_make=6 calling_build=2 apply_patch=3）
#   → G1/G0/G2/G3/G4/L4/L5 PASS；L2 跳过（纯库无 bin/，人工补测 reports/conan-verify-supplement.md）
#   → test_package 20/20（reports/conan-create.log:383）
#   → W3 本地 CI exit_code=0，Total 1 / Success 1（reports/w3-local-ci.log、.ci-result.json）
#   → 证据链 capture_evidence --verify rc=0（conan-create.log / conan-verify-report.md / w3-local-ci.log 三份与副本一致）
```

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libgta.so.1.0.0`（SONAME `libgta.so.1`，NEEDED 仅 libc.so，`.codesign` 段在）+ `lib/libgta.so*` 软链 | 动态库 |
| `lib/libgta.a` | 静态库（shared=Off 时唯一产物） |
| `include/gta/{gta.h,gta.hpp,gta_version.h}` | 头文件 |
| `lib/pkgconfig/gta.pc` | pkg-config（配方 `pkg_config_name=gta` 与之对齐） |
| `share/doc/libgta/example-*.{c,cpp}`（8 个） | 上游示例 |
| `licenses/COPYING` | LGPL-2.1（源码头声明 or later → `LGPL-2.1-or-later`） |

安装树无 `bin/` → 纯库包，不建 commands.json（R38/PF8）。

## 注意事项

- `make check` 的 fuzztest SKIP 是上游设计而非环境缺口，PR 正文按声明 N=8 / N′=8 / PASS=7 / SKIP=1 如实申报（SKIP 只有 fuzztest.sh，附上游脚本原话归因），差额与四口径归因见 `reports/test-report.md`。
- 上游 `endianness` 用例由 `WITH_COMPRESSION` 门控（默认 off），不在 TESTS 注册面内，不计入 N。
- CMake 入口默认 `GTA_BUILD_DOCUMENTATION=ON` 会 `find_package(Doxygen REQUIRED)` 且不注册 tests——本任务不走 CMake 入口（manifest 选 autotools）。
- 探索期曾用 `rm -rf tests/fuzztest-*` 清理临时 fuzz 目录，误删上游 `fuzztest-create.c/fuzztest-check.c`（同前缀通配），已从 `.orig` 原样恢复并复跑 make/check 双绿；tracker 复核源码面改动恒为 3 个文件（config.guess/config.sub/configure）。
