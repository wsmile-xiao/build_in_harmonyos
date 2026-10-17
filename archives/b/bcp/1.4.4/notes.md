# bcp 1.4.4 适配笔记

## 编译环境
- 构建系统: autotools（官方 release tarball 自带预生成 configure；直接驱动
  `Bcp/` 子包 configure，顶层 configure 仅做子包编排）
- 编译日期: 2026-09-23
- 编译器: /data/service/hnp/bin/clang（OHOS clang 15, aarch64-unknown-linux-ohos）
- 状态: built

## W0 四关预检结论（生死关，2026-09-23 实核，证据 $TASK_DIR/w0/）
1. **版本可得性**：官方 `https://www.coin-or.org/download/source/Bcp/Bcp-1.4.4.tgz`
   可达；双域独立下载 sha256 全等
   `8b490ad35c28a79806f84dacbdc36d602ce0a3a4e32c3575f99495c6e6b4906e`
   （coin-or.org 官方 vs coin-or.clemson.edu 异域镜像，7553768 字节）；
   Debian 池无件（coinor-bcp 仅 RFP #549417 从未打包）；Fedora coin-or-Bcp-1.4.4
   RPM 旁证；tarball 内证 `configure.ac:15 AC_INIT([Bcp],[1.4.4],...)`；上游 git
   tag `releases/1.4.4`（cbd92b1）。
2. **硬依赖**：真实 `conan install --build=missing`（-pr:h/-pr:b 双传绝对路径
   ohos-aarch64 profile）rc=0；coinutils/2.11.13、coin-or/0.108.12、clp/1.17.10、
   cgl/0.60.10.1、vol/1.5.4（Bcp 特有）、zlib/1.3.1 全二进制可得无冲突，
   钉版与已发布 coinor-cbc 2.10.13 闭包一致。可选求解器（Cpx/CPLEX/MPI/Xpress）
   缺省禁用。
3. **平台可移植性**：全仓 grep 字面命中 immintrin 4 文件，**全部位于捆绑 Clp/
   子树**（Bcp 自身 0 命中、printf 钩子 0）；aarch64 clang15 一手探针
   `#include <immintrin.h>` rc=1（#error x86 only）、cpuid asm rc=1。编排方裁决
   （2026-09-23）：外部依赖 flags 模式下捆绑子树不进编译面 → 判不止损（裁量
   登记见问题表 #1）。
4. 无缺失硬依赖 → 无前置任务清单。

## 集成口径（为什么是外部依赖 flags 模式）
1. 官方 tarball `Dependencies` 声明 5 硬依赖但**同时捆绑全部 5 个子树**
   （CoinUtils/Osi/Vol/Clp/Cgl）；捆绑 Clp 含无条件 `#include <immintrin.h>`
   （ClpSimplexDual.cpp:3556、ClpPackedMatrix.cpp:6753），OHOS aarch64 必编译
   失败（探针实证）→ 绝不能让它进编译面。
2. `Bcp/configure` 的 `--with-<pkg>-incdir / --with-<pkg>-lib` flags 分支直接
   置 `coin_has_*=yes` 并跳过 pkg-config 与捆绑检测（configure:20774 clp、
   21799 vol、22309 cgl 实证）；顶层 configure 仅在 bundled 分支才
   `subdirs="$subdirs Clp"`（:21245），`Bcp/Makefile.am` 的 SUBDIRS 只有 src →
   外部依赖时 5 个捆绑子树全部不参与构建。
3. 已发布依赖包 .pc 固化 `prefix=/` 不可作消费路径（coinor-cbc 问题表 #7 同族）
   → 五包头合并 generators 目录单一 staging 供三个 incdir 共用；闭包链接串按
   「依赖方在前」**直连 .a 路径**展开（-l 形式会被 .la 的 `libdir='//'` 解析成
   `//lib/*.la` 死路）。
4. `Bcp/configure` 只查 Clp（必填，Cpx 备选）/Vol/Cgl，无 coinutils/osi flags
   分支 → coinutils/osi 的头经 staging 的 -I 覆盖，库进各闭包串。
5. 不给 `--with-mpi` → `AC_COIN_CHECK_USER_LIBRARY` 探不到 mpi.h 置
   `coin_has_mpi=no`（MPI 的 AM_CPPFLAGS 有 conditional 包裹，安全）。

## 编译步骤（配方 build() 内固定序，全部源码树 Bcp/ 子目录 in-source）
1. shebang/config.guess HMDFS 修复（7 脚本 × 根与 Bcp/ 两层）
2. configure（flags 模式；`CFLAGS/CXXFLAGS='-O3 -pipe -DNDEBUG'` 显式钉死——
   CI 环境泄漏 `-fPIC -O2` 无 -DNDEBUG，不钉会分叉，见问题表 #3）
3. config.status HMDFS 修复（umask 077→022、mktemp→conftmp）后重跑
4. `make -j1`（MAKEFLAGS=''，防 jobserver 与 HMDFS .lo 并发截断）
5. `.lo` 修复（src、test/BAC）
6. 上游测试三步：`make -C test/BAC unitTest` → unitTest ELF 自签 → `make test`
7. `package()`: `.lo` 修复 → `make install DESTDIR=` → LICENSE

## 上游测试面
- `Bcp/Makefile.am`: `TESTS = BAC`；`test: all → (cd test/$$t; make test)`；
  test/BAC 的 `test: unitTest` → `./unitTest -param bb.par`
- test/BAC 不在默认 SUBDIRS（`if ALWAYS_FALSE`）→ 必须显式编译（问题表 #2）
- unitTest = 7 个上游源（LP/BB_lp、TM/BB_tm、Member/BB_{user_data,packer,init,cut}、
  Member/BB）链接 libBcp.la；场景 = examples/BAC 的 bac.lp/bac.mps +
  bb.par（Benders branch-and-cut，串行消息传递单进程）
- 注册测试目标数 N = 1（TESTS=BAC 单程序单场景；四口径清点：源码宏 0 /
  框架注册 1 / assertion 0 / 消费者断言 10，不混用）
- 消费者测试 = test_package/main.cpp 10 断言（版本宏 4 + buffer 3 + cg_prob 3）

## 问题表
| # | 现象 | 根因 | 处置 |
|---|---|---|---|
| 1 | W0-3 全仓 grep 字面命中 `immintrin.h`（4 文件）+ x86 内联 asm，读起来像平台不可移植 | 命中全在**捆绑 Clp/ 子树**（Bcp 自身 0 命中）；ClpSimplexDual.cpp:3556、ClpPackedMatrix.cpp:6753 为非 MSVC 无条件 include，aarch64 clang15 探针 `#include <immintrin.h>` rc=1（#error x86 only）、cpuid/prefetchnta asm rc=1；其余命中在 `#if AVX2==…`/`#ifdef COIN_PREFETCH`（默认注释关）/`#if 0` 死块 | 外部依赖 flags 模式使捆绑子树不进 SUBDIRS → 命中不在构建面，编排方裁决（2026-09-23）不止损；**自证**：configure/编译日志不得出现 `Clp/` 目录编译行（采信轮 G2 留意）；**复发条件**：若未来被迫启用 bundled Clp，探针 rc=1 即转强制路径，按 W0-3 止损重判 |
| 2 | `make all` 后 `make test` 找不到 unitTest | test/BAC 在 `if ALWAYS_FALSE` 下不进默认 SUBDIRS，上游设计是「用户显式 make test 才编译」 | build() 三步驱动：显式 `make -C test/BAC unitTest` → OHOS ELF 自签（签名必须在执行前且签名后不重编，故不并入 make test）→ `make test` |
| 3 | CI 环境泄漏 `CFLAGS/CXXFLAGS=-fPIC -O2`（无 -DNDEBUG）会污染 configure | worker 进程环境泄漏（knowledge/FAQ.md 记载值），profile 与 ci/ 脚本均不设置 | 配方 configure 处显式钉 `CFLAGS/CXXFLAGS='-O3 -pipe -DNDEBUG'`（coinor-cbc/ositests Segv 同族教训，R33 纪律） |
| 4 | 依赖闭包若用 `-L/-l` 形式，libtool 报 `not a valid libtool archive` | 已发布 COIN-OR 包 .la 固化 `libdir='//'`（prefix=/ 构建） | 闭包串一律直连 `<pkg>/lib/*.a` 绝对路径（coinor-cbc 探索轮同款） |
| 5 | `BcpConfig.h` 版本宏来源 | 安装的 `include/coin/BcpConfig.h` = `install-exec-local` 从 configure 生成的 `include/config_bcp.h` 拷入（含 `BCP_VERSION "1.4.4"`），源码里的 BcpConfig.h 壳不安装 | test_package 直接 `#include <BcpConfig.h>` 断言 4 条版本宏 |
| 6 | build1 configure 早期失败：`Invalid configuration 'aarch64-unknown-linux-musl': machine 'aarch64-unknown-linux' not recognized` | tarball 的 config.guess/config.sub 为 2007-04-29 / 2011 版（顶层与 Bcp/ 各一份），CPU 表 0 处 aarch64；且设备 `uname -s = HarmonyOS` 老 config.guess 不识别 | 4 个 portability 补丁（与 coinor-dylp 1.10.4 同源，对本包 dry-run 全过）：config.sub 补 aarch64+linux-musl、config.guess 补 HarmonyOS/HongMeng 与 aarch64:Linux 分支直接输出 unknown-linux-musl；经 conandata `patches:` + manifest `patches_applied` 两面同步登记，build() `apply_conandata_patches` 应用 |
| 7 | build2 的 test_package 编译 3 errors：`ISO C++17 does not allow dynamic exception specifications`（`BCP_buffer.hpp:104/110/224` `throw(BCP_fatal_error)`）；随后本地预验又发现消费者真跑 `-O3` **Segmentation fault**（`-O0` 10/10 过） | ①标准代差：profile cppstd=17 传 `-std=c++17`，而主包 autoconf 构建未传 -std（clang15 默认 gnu++14，动态异常规格 deprecated 仍合法）；②运行时：**上游 `BCP_cg_prob` 构造初始化列表未含 `packer` 成员**（`Bcp/src/CG/BCP_cg.cpp` ctor 只初始化 user/msg_env/core/upper_bound/phase），析构第一句 `delete packer` 吃栈垃圾指针——O0 恰好栈零侥幸、O3 必崩；unitTest 因 USER_initialize 先赋值 packer 而不触发（上游缺陷非本适配引入） | ①test_package `std_flag` 钉 `-std=gnu++14` 与主构建同源（编排方裁决 2026-09-23 A，不动上游头）；②消费者按公开成员契约在析构前显式 `prob.packer = NULL`（delete NULL 安全），main.cpp 注释与本表如实登记上游未初始化缺陷；二分证据（a/b/c/d/e/f/g 七组 O0/O3 对照）留 `$TASK_DIR/bisect/` |
| 8 | 链接日志 `ld.lld: warning: … archive member 'libX.a' is neither ET_REL nor LLVM bitcode`（build4 计 144 处） | libtool 静态链接把 `libBcp_la_LIBADD` 的直连 `.a` **嵌套归档**进 `libBcp.a`；lld 对嵌套 .a 成员跳过（非目标文件），**符号由外层显式 `.a` 闭包串解析**——非阻断警告族（coinor-cbc/mksh 同款先例） | 如实记录不处置：unitTest 与 test_package 消费者**实跑双过**（build4 rc=0、10/10），闭包串已在 configure flags 与 test_package link 两处显式展开，不依赖嵌套成员 |

## 状态
built：build4 `conan create` rc=0 全链（configure flags 模式 → 67 对象全 Bcp/src → unitTest 显式编译+ELF 自签 → `make test`（`./unitTest -param bb.par`）rc=0 → install DESTDIR → test_package 消费者 **10/10**，error 计数 0）；采信轮 `conan_verify_round.sh` rc=0 干净轮（证据三份+finish 前快照，finish 前已脏 0）。捆绑子树窄/宽双形态 grep 双日志（build2+build4）全 0 = W0-3 裁量闭环自证。
