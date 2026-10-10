# libvmdk 20260714 适配笔记

## 编译环境

- 构建系统: autotools（发行 tarball 自带预生成 configure/Makefile.in，无需 autoreconf）
- 编译日期: 2026-10-09
- 编译器: clang 15.0.4（OHOS 工具链，Target: aarch64-unknown-linux-ohos）
- 状态: built

## 源码溯源（2026-10-09 实测）

1. 上游 GitHub（libyal/libvmdk）`git ls-remote --tags` 返回
   `refs/tags/20260714`（commit `396e1873a030ac535bf919f6707d5be57613ae08`）
   ——任务卡版本 20260714 对应 tag **存在**（同场 20240510=`34890e3d` 亦在）。
2. release 资产按 libyal 三通道逐一 HTTP 探测（通道名不可先验）：
   - `libvmdk-alpha-20260714.tar.gz` → **200**（本配方采用，channel=alpha，
     1624602 字节，sha256 `8f429818aac09bd0457e6f550d39e705787856f7523d7b3c82caa8ee759678b1`）
   - `libvmdk-experimental-20260714.tar.gz` → 404
   - `libvmdk-20260714.tar.gz` → 404/不可达
3. **任务卡给定 codeload 通道的取舍**（本版与 20240510 任务的关键差异）：
   - codeload git tarball（refs/tags/20260714）HTTP 200 可达（296256 字节），
     但它是**裸源码快照**：不含 configure/Makefile.in/config.guess/config.sub
     预生成产物，也**不含** 13 个 libyal 支持子库目录（tar tzf 实证顶层无
     libcerror 等）。
   - 补齐需要 synclibs.sh（对每个子库 `git clone https://github.com/libyal/<lib>.git`
     再 sed 改写 Makefile.am）+ autogen.sh（autoreconf --force --install）；
     前者把未注册 vendored 依赖拉进 PR，违反本仓同族配方明文的
     "never pulls unregistered dependencies" 规范（libvhdi/libpff/libolecf
     先例的 build() 闭包检查均为拒绝 synclibs），后者需要 CI worker PATH 有
     automake——20240510 notes 先例已实证 worker 无 automake，bootstrap 路线
     在 CI 不可行。
   - release alpha 资产是上游发布流水线 synclibs+autogen 后的**自包含快照**
     （configure/Makefile.in/aclocal.m4/config.guess/config.sub + 13 子库全在），
     与同仓 20240510 先例完全同通道同规范，故采用。
4. tarball 顶层目录 `libvmdk-20260714/`：预生成 `configure`/`Makefile.in`/
   `config.guess`/`config.sub`（**2025-07-10 vintage**，比 20240510 的
   2023-06-23 新两代）；`AC_INIT([libvmdk],[20260714])` 版本一致。
   Debian 池（deb.debian.org/debian/pool/main/libv/libvmdk/）最高仅 20240510，
   无 20260714 同源通道可对拍。

## W0 依赖发布检查：唯一外部依赖 zlib/1.3.2

1. **捆绑清点**：发行 tarball 顶层含 13 个 libyal 支持组件目录（`libbfio
   libcdata libcerror libcfile libclocale libcnotify libcpath libcsplit
   libcthreads libfcache libfdata libfvalue libuna`，另加顶层 `common/`
   共享支撑代码）——与 `configure.ac` 的 spec-requires 列表及
   `AX_LIB*_CHECK_ENABLE` standalone 宏族对应；configure 汇总面实测
   13 项全部 `local`。这些**不是** Conan 依赖。
2. **外部依赖**：`AX_ZLIB_CHECK_ENABLE` / `AX_ZLIB_CHECK_UNCOMPRESS`——
   `libvmdk_compression.c`、`libvmdk_deflate.c`、`libvmdk_grain_data.c` 直接
   include `zlib.h` 并调用 `uncompress()`（压缩 grain 数据解压的硬依赖）。
   configure 汇总面实测 `DEFLATE compression support: zlib`。
3. **发布检查**：ohpcd 制品仓 `zlib/1.3.2` 已发布（conan list 实证，
   20240510 任务已用同版本消费其 ohos-aarch64 二进制）。
4. **接线 = AutotoolsDeps 单通道**：`generators = "AutotoolsDeps"`（afflib 等
   500+ 主线先例，zlib 的 include/lib 经 conanbuild 聚合环境注入
   CPPFLAGS/LDFLAGS），configure 走**自动探测**路径成功。
   **不加 `--with-zlib=<DIR>`**：本版随包 `m4/zlib.m4`（Version 20260622）的
   DIR 分支仍以 `zlib` 置成功态（grep 实测 `ac_cv_zlib=zlib` 赋值点），沿
   20240510 的 DRAFT-E724 结论（round-1 G2 实测 "unable to find supported
   zlib in directory"），显式 DIR 参数不用。
5. **可选依赖 libfuse**：configure 汇总面 `FUSE support: no` → 上游默认
   条件编译降级（见「已知限制」），不算止损。

## W0-3 平台可移植性

- 纯 C，无 ISA 专属头、无 glibc printf 钩子族（同 20240510 口径）。

## 编译步骤（配方实际序列）

conanfile.py `build()` 内（OHOS 分支）：

1. `os.umask(0o022)` 全程保持 022；
2. `_patch_hmdfs_umask()`：随包 configure 内 2 处 `umask 077` → `022`（E011）；
3. `/data/service/hnp/bin` 前置进 PATH（本版测试框架 autom4te 需要，见
   「上游测试」节），`CONFIG_SHELL=/data/service/hnp/bin/bash`（profile
   [buildenv] 注入）显式启动 configure，参数由 AutotoolsToolchain 统一构造：
   `--disable-python --enable-static-executables=no --enable-shared
   --disable-static --build=aarch64-unknown-linux-gnu
   --host=aarch64-unknown-linux-gnu`；
4. `make -j2`（显式限并发）；
5. `make -j2 check LOG_COMPILER="<bash>"`，进程子树内临时把 `libvmdk/.libs`
   前置进 `LD_LIBRARY_PATH`（测试程序读回树内共享库），退出还原。

`package()`：`make install DESTDIR=<pkg>` + 删除 `lib/*.la` + 拷贝
`COPYING`/`COPYING.LESSER` 到 `licenses/`。

原生构建（非 conan，沙箱）同参数实测（2026-10-09）：
configure rc=0（zlib 探测 yes、13 子库 local）→ make -j2 rc=0 →
make -j1 check rc=0（autotest 链路设备真跑，读数见下节）→
make install DESTDIR rc=0（安装树：头文件 7、libvmdk* 5、bin 2、pkgconfig 1）。
证据 `~/tmp/libvmdk-20260714/native-{configure,make,check,install}.log`。

## 平台适配（全部内联在 `conanfile.py build()`，无 `patches/` 文件）

| # | 事实 | 依据 |
|---|------|------|
| 1 | E011：configure 内 2 处 `umask 077` → `022`，全程 umask 022 | HMDFS 目录模式落盘后不可改，同族 libsmraw/libvsgpt/20240510 同口径 |
| 2 | 三元组：`--build/--host=aarch64-unknown-linux-gnu`（update_configure_args 替换语义） | 本版 config.guess（2025-07-10 vintage）设备实测 `uname -s=HarmonyOS` → "unable to guess system type" 硬失败（config.sub 虽接受 linux-ohos，guess 环节仍挂）；显式三元组绕过 |
| 3 | `CONFIG_SHELL` 指向绝对路径 bash 启动 configure | OHOS 无 `/bin/bash`，`/bin/sh` 是 toybox；同族先例 |
| 4 | make 前 `/data/service/hnp/bin` 前置 PATH | 本版测试框架迁 autotest：`.at → autom4te` 生成套件脚本；hnp 自带 autom4te（autoconf 2.72），CI worker 缺 automake 但 hnp 路径可解析（profile buildenv 已含该 PATH，配方显式兜底） |
| 5 | 测试程序运行期把 `libvmdk/.libs` 前置进 `LD_LIBRARY_PATH` | 共享库模式下 automake 测试需要读回树内 libvmdk.so；同族先例 |
| 6 | `--disable-python` | pyvmdk 绑定不入交付面；`HAVE_PYTHON_TESTS` 不成立，test_python_module 不入注册面 |

## 上游测试（`make check`，构建期在 build() 内执行，autotest 结构）

本版测试框架相对 20240510 的重大变化：**已从 shell 入口脚本（TESTS）迁移到
autotest**（`tests/*.at` 构建期经 autom4te 生成 `test_library`/
`test_manpages`/`test_tools` 套件脚本，`check-local` 驱动执行）。

清点口径 = `tests/Makefile.am` 的两个注册面（libyal 家族口径延续）：

| 注册面 | 数量 | 实测（native-check.log） |
|---|---|---|
| `check_AUTOTESTS`（autotest 套件） | 3 | test_library 16 用例 ok + test_manpages 3 skipped + test_tools 3 用例 ok |
| `check_PROGRAMS`（C 测试程序） | 21 | 21 个全部构建（16 无输入 + 3 tools 由套件执行；handle/support 属 WITH_INPUT 形态，input/ 夹具缺失时套件不展开带输入用例，程序本体仍构建） |
| **合计（N）** | **24** | **19 执行通过 + 5 上游规则 skip** |

- 逐字读数（autotest 套件汇总）：`Running library tests. All 16 tests were
  successful.` / `Running manpages tests. 0 tests were successful. 3 tests were
  skipped.` / `Running tools tests. All 3 tests were successful.`
- **skip 归因（5 项，全部上游规则）**：
  - test_manpages 3 项（libvmdk.3/vmdkinfo.1/vmdkmount.1）：
    `AT_SKIP_IF(test -n "${SKIP_MANPAGES_TESTS}")` + `MANPAGE_LINTER="no"`
    （configure 默认未配置 man-db/mandoc linter，atlocal 实证）→ 上游 lint
    规则 skip；
  - handle/support 的 WITH_INPUT 用例不展开：发布 alpha 资产不含
    `tests/input/` 夹具（tar tzf 实证 0 命中），generate_test_inputs.sh 在
    input/ 缺失时生成空 `test_inputs_*.at`（`m4_define([], [[]])` 形态），
    `RUN_TEST_BINARIES_WITH_INPUT` 的 m4_foreach_w 空列表零展开——用例不
    注册（与 20240510 的"退化为无输入运行"不同，本版是注册面直接不含）。
- `check_AUTOTESTS` 内条件项 `test_python_module`（`if HAVE_PYTHON_TESTS`）
  因 `--disable-python` 不成立，未进入注册面，不计入 N。
- autom4te 依赖实证：设备原生轮 make check rc=0，套件脚本由
  `/data/service/hnp/bin/autom4te`（autoconf 2.72）生成成功。

## 消费者测试（`test_package/`，Conan L1）

- 从 20240510 平移（API 面逐项核对：28 个 libvmdk_* 公开符号全在
  include/libvmdk.h，LIBVMDK_DISK_TYPE_MONOLITHIC_FLAT/ACCESS_FLAG 常量
  不变），仅版本断言更新为 20260714。
- `test_libvmdk.c`（**41 项断言**）：版本串、access flags、codepage 三路、
  VMDK 签名探测三路、合成 monolithicFlat VMDK 全链路读回、EOF 语义、
  错误路径、生命周期。
- `test_ohos.c`（**31 项断言**，仅 OHOS 编译运行）：`__OHOS__` 编译目标、
  TMPDIR 语义、TMPDIR 下合成 monolithicFlat VMDK 并读回全链路（含跨扇区
  边界读、尾部读、open 前置 set_max_open_handles、signal_abort、错误回溯）。
- `vmdkinfo -V`：安装后的 CLI 产物加载共享库并输出版本串（运行/加载验证，
  test() 内执行）。
- 两程序断言合计 **72**；合成夹具语义沿用 DRAFT-E726（camelCase
  createType + 显式 open_extent_data_files + open 前置 set_max）。

## 与 20240510（同仓上一版）的差异清单

| 维度 | 20240510 | 20260714 |
|---|---|---|
| 测试框架 | TESTS shell 脚本（test_library.sh 等） | autotest（.at + autom4te） |
| config.guess/sub vintage | 2023-06-23（不识别 linux-ohos） | 2025-07-10（sub 接受 ohos，guess 仍无法识别 HarmonyOS） |
| m4/zlib.m4 | 20240314 | 20260622（DIR 分支行为同，仍不加 --with-zlib） |
| 上游 N | 24（TESTS 3 + check_PROGRAMS 21） | 24（check_AUTOTESTS 3 + check_PROGRAMS 21） |
| 实测读数 | 23 通过 + 1 skip | 19 执行通过 + 5 上游规则 skip |
| make check 额外依赖 | 无（bash 即可） | autom4te（hnp 提供，PATH 前置兜底） |
| 源通道 | release alpha 资产（Debian 可对拍） | release alpha 资产（Debian 无此版，codeload 裸快照不可用） |

## 已知限制

1. `vmdkmount` 的 FUSE 挂载功能：OHOS/CI 无 libfuse（configure 汇总面
   `FUSE support: no`），mount 路径按上游 `#if defined(HAVE_LIBFUSE)` 守卫
   **编译期降级**（工具本体与 `-V` 不受影响）。`vmdkinfo` 全功能不受影响。
2. test_manpages 3 项 skip：上游默认未配置 MANPAGE_LINTER（man-db/mandoc
   均不在 worker PATH），按上游 AT_SKIP_IF 规则 skip——替代验证：手册页
   由构建系统安装（`manuals/*.1/3` 走 make install 的 man_MANS 面），且
   test() 内 `vmdkinfo -V` 做 CLI 实跑。
3. handle/support 的 WITH_INPUT 用例不展开：发布 alpha 资产不含
   `tests/input/` 夹具（上游发布流水线 synctestdata 不入 release tarball，
   属上游设计）——替代验证：消费者测试以合成 monolithicFlat VMDK 覆盖
   handle/support 的公开 API 面（open/read/seek/EOF/生命周期，DRAFT-E726）。
4. `libvmdk_handle_set_maximum_number_of_open_handles()` 的 pool 已建分支
   上游缺陷（DRAFT-E726 登记）：测试按「open 前调用」的正确姿势规避，
   缺陷本身未修（不改上游源码）。
5. CI 探针长选项：libyal 工具只接受短选项 `-V`/`-h`（`--version` 会 rc=1）；
   产物加载由 test_package 的 `vmdkinfo -V`（conanrun 环境）单独覆盖。
