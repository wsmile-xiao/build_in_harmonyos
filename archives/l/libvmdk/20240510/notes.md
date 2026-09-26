# libvmdk 20240510 适配笔记

## 编译环境

- 构建系统: autotools（发行 tarball 自带预生成 configure/Makefile.in，无需 autoreconf）
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4（OHOS 工具链，Target: aarch64-unknown-linux-ohos）
- 状态: built

## 源码溯源（2026-09-25 实测，三方同源）

1. 上游 GitHub（libyal/libvmdk）`git ls-remote --tags` 返回
   `refs/tags/20240510`（commit `34890e3d1cb34b06502ec789fbea764d38817207`）
   与 `refs/tags/20260714`；任务卡版本 20240510 对应的 tag **存在**。
2. release 资产按 libyal 三通道逐一 HTTP HEAD 探测（同族 libsmraw 资产 404、
   libfsapfs 资产存在——通道名不可先验）：
   - `libvmdk-alpha-20240510.tar.gz` → **200**（本配方采用，channel=alpha）
   - `libvmdk-experimental-20240510.tar.gz` → 404
   - `libvmdk-20240510.tar.gz` → 404
   - 注：`api.github.com` 匿名限流（rate limit exceeded）不构成「无 release」
     结论（device-facts §一.29），资产可用性一律以直连 HEAD 为准。
3. **双通道字节级同源**：上游 alpha 资产与 Debian 池 pristine orig tarball
   （`deb.debian.org/debian/pool/main/libv/libvmdk/libvmdk_20240510.orig.tar.gz`）
   `cmp` **逐字节一致**（均 1659682 字节），sha256
   `985966c252cb9cf252e594830f0889f7b74250604b1d5705c799b120e66b9b9c`
   与 PGP 签名的 `libvmdk_20240510-2.dsc`（`BEGIN PGP SIGNATURE` 计数 = 1）
   的 `Checksums-Sha256` **逐字一致**（.dsc 内 sha1/md5 行不采信）。
4. tarball 顶层目录 `libvmdk-20240510/`：预生成 `configure`/`Makefile.in`/
   `config.guess`/`config.sub`（timestamp 2023-06-23，与 libsmraw 20240506、
   libvsgpt 0-20240504 同 vintage）——无需 autoreconf（这点对 CI 关键：
   worker PATH 没有 automake）。

## W0 依赖发布检查：唯一外部依赖 zlib/1.3.2

1. **捆绑清点**：发行 tarball 顶层含 13 个 libyal 支持组件目录（`libbfio
   libcdata libcerror libcfile libclocale libcnotify libcpath libcsplit
   libcthreads libfcache libfdata libfvalue libuna`，另加顶层 `common/`
   共享支撑代码）——与 `configure.ac` 的 spec-requires 列表（13 项，逐项比对
   一致）及 `AX_LIB*_CHECK_ENABLE` standalone 宏族对应；这些**不是** Conan 依赖
   （`--with-lib*` 不给 DIR 时用内嵌副本）。
2. **外部依赖**：`AX_ZLIB_CHECK_ENABLE` / `AX_ZLIB_CHECK_UNCOMPRESS`——
   `libvmdk_compression.c`、`libvmdk_deflate.c`、`libvmdk_grain_data.c` 直接
   include `zlib.h` 并调用 `uncompress()`（压缩 grain 数据解压的硬依赖）。
3. **发布检查**：`conan list -r=ohpcd "zlib/*"` 有 1.3.1..1.3.2 多版本；真实
   可用性证据按 §4.1 只认 `conan install`：
   `conan install --requires=zlib/1.3.2 --profile:host=<ohos-aarch64>
   --build=never` **rc=0**，直接下载 ohpcd 上的 ohos-aarch64 二进制
   （package id `6b129b068851896169fae42d399fa922d239ce8a`）。
   清单落 `$TASK_DIR/w0-deps.txt`（单行 `zlib/1.3.2`）。
4. **接线 = AutotoolsDeps 单通道**：`generators = "AutotoolsDeps"`（afflib 等
   500+ 主线先例，zlib 的 include/lib 经 conanbuild 聚合环境注入
   CPPFLAGS/LDFLAGS），configure 走**自动探测**路径成功，实测两路探测真绿：
   `checking for zlib.h... yes`、`checking for uncompress in -lz... yes`
   （编译行可见 `-I.../.conan2/p/zlibadde02423c9a0/p/include`）。
   **为什么没有 `--with-zlib=<DIR>` 第二通道**：本版共享 `m4/zlib.m4`
   （Version 20240314）的 DIR 分支把成功态置 `ac_cv_zlib=zlib`，而收尾终闸判
   `ac_cv_zlib != yes`（生成的 configure 54448–54649 全部赋值点仅
   no/check/zlib，`yes` 从未被赋值）⇒ 显式 DIR 参数**必然** configure 失败；
   采信轮 round-1（G2）实测 `configure: error: unable to find supported zlib in
   directory: /…/zlibadde02423c9a0/p`（逐字证据 `$TASK_DIR/round1-archive/
   conan-create.log:421`；`reports/conan-create.log` 是 round-3 干净轮日志、
   该串 0 命中），移除该参数后 round-2 的 configure/构建阶段越过该错误，但
   **round-2 仍 G2 FAIL**（另一独立问题：消费者测试断言缓冲 512 不足，另修
   `a5b30e5c8`），**G2 整体转绿在 round-3 干净轮**——上游 m4 缺陷已登记
   DRAFT-E724。
   **A/B 对照（E724 证据）**：OHOS SDK sysroot 自带 `zlib.h`/`libz.so`，无接线的
   裸 configure 同样两探测 yes ⇒ 探测读数不可单独采信；决定性判据在链接产物面——
   接线构建 `readelf -d libvmdk.so.1.0.0` NEEDED **仅 `libc.so`**（`llvm-nm -D`
   中 `uncompress`/`inflate*` 全为 `T`，conan libz.a 静态内嵌、自包含），裸路径
   对照构建（`$TASK_DIR/neg-zlib`）NEEDED = `[libz.so]` + `[libc.so]`
   （动态依赖 sysroot，逐字证据 neg-zlib-make.log）。
5. **可选依赖 libfuse**：`checking for fuse.h... (cached) no` → 上游默认
   条件编译降级（见「已知限制」），不算止损。

## W0-3 平台可移植性

- `grep -rIlE 'altivec\.h|<mmx|3dnow|immintrin|xmmintrin|register_printf_|<printf\.h>'`
  对全部 `*.c/*.h/*.ac/*.am` **rc=1 无命中**（纯 C，无 ISA 专属头、无 glibc
  printf 钩子族）。
- W0 三关（版本可得性 / 硬依赖发布 / 平台可移植）全过后才写配方。

## 编译步骤（配方实际序列）

conanfile.py `build()` 内（OHOS 分支）：

1. `os.umask(0o022)` 全程保持 022；
2. `_patch_hmdfs_umask()`：随包 configure 内 2 处 `umask 077` → `022`（E011，
   HMDFS 上按 077 建出的 0700 临时目录连创建者都不可写）；
3. `CONFIG_SHELL=/data/service/hnp/bin/bash`（profile [buildenv] 注入）显式启动
   configure，参数由 AutotoolsToolchain 统一构造：
   `--disable-python --enable-static-executables=no --enable-shared
   --disable-static --build=aarch64-unknown-linux-gnu
   --host=aarch64-unknown-linux-gnu`（zlib 不带 `--with-zlib` 参数，走
   AutotoolsDeps 注入的 CPPFLAGS/LDFLAGS 自动探测，见 W0 节第 4 条）；
4. `make -j2`（显式限并发：os.cpu_count()=20 而 affinity=8，默认会 2.5× 超订）；
5. `make -j2 check LOG_COMPILER="<bash>"`，进程子树内临时把 `libvmdk/.libs`
   前置进 `LD_LIBRARY_PATH`（测试程序读回树内共享库），退出还原。

`package()`：`make install DESTDIR=<pkg>`（AutotoolsToolchain 默认
`prefix=/`，落成 `pkg/{include,lib,bin}`）+ 删除 `lib/*.la` + 拷贝
`COPYING`/`COPYING.LESSER` 到 `licenses/`。

原生构建（非 conan，SKILL §3 Step 2，沙箱 HOME）同参数实测：
configure rc=0 → make rc=0（`libvmdk/.libs` 3 个 .so 实物、vmdkinfo+vmdkmount
均产出）→ make install DESTDIR rc=0（安装树清点：头文件 7、libvmdk* 5、bin 2）
→ make check rc=0。证据 `$TASK_DIR/native-build.log`（NATIVE_BUILD_RC=0）。

## 平台适配（全部内联在 `conanfile.py build()`，无 `patches/` 文件）

| # | 事实 | 依据 |
|---|------|------|
| 1 | E011：configure 内 2 处 `umask 077` → `022`，全程 umask 022 | HMDFS 目录模式落盘后不可改（0700 连创建者不可写），同族 libsmraw/libvsgpt/libfsapfs 同口径 |
| 2 | 三元组：`--build/--host=aarch64-unknown-linux-gnu`（update_configure_args 替换语义） | 随包 config.sub（2023-06-23 vintage）不识别 `linux-ohos`；同族 libvsgpt/libsmraw 设备实测 `OS 'ohos' not recognized`（同 vintage 先例采信，conan create 干净轮全绿即证参数有效） |
| 3 | `CONFIG_SHELL` 指向绝对路径 bash 启动 configure；make check 用 `LOG_COMPILER` 指定同一 bash | OHOS 无 `/bin/bash`，`/bin/sh` 是 toybox；libyal TESTS 全是 bash 脚本（shebang `#!/usr/bin/env bash`） |
| 4 | 测试程序运行期把 `libvmdk/.libs` 前置进 `LD_LIBRARY_PATH`（只作用本进程子树） | 共享库模式下 automake 测试需要读回树内 libvmdk.so；同族先例 |
| 5 | `--disable-python` | pyvmdk 绑定不入交付面；`HAVE_PYTHON_TESTS` 条件不成立，`test_python_module.sh` 不进 TESTS（不计入上游 N）。上游 `--enable-python` 默认即 no，显式声明是意图留痕 |

## 上游测试（`make check`，构建期在 build() 内执行）

清点口径 = `tests/Makefile.am` 的**两个 automake 注册面**（libyal 家族口径，
同 libsmraw/20240506、libvsgpt/0-20240504 先例）：

| 注册面 | 数量 | 实测 |
|---|---|---|
| `TESTS`（shell 入口脚本） | 3 | `PASS 2`（test_library.sh、test_tools.sh）＋ `SKIP 1`（test_vmdkinfo.sh，exit 77） |
| `check_PROGRAMS`（C 测试程序） | 21 | 21/21 真实执行且通过（test_library.sh 驱动 18 个 + test_tools.sh 驱动 3 个，`Testing: …(PASS)` 逐条读数在 `tests/*.log`，FAIL 0） |
| **合计（N）** | **24** | 见 PR 正文与 reports/（按最终设备日志复算） |

- runner 级读数（automake test-driver 汇总，逐字）：`# TOTAL: 3 / # PASS: 2 /
  # SKIP: 1 / # FAIL: 0 / # ERROR: 0`；`TOTAL = PASS + FAIL + SKIP + NOT_RUN`
  ⇒ 3 = 2 + 0 + 1 + 0（入口脚本口径），程序口径 21 = 21 + 0 + 0 + 0。
- **驱动关系**：`test_library.sh` 的 `LIBRARY_TESTS`（16 个，无输入）+ 尾部
  `for … if test -d "input" … else run_test` 分支——**input/ 缺失时
  handle/support 退化为无输入运行，不是跳过**（脚本级 FAIL 0 与失败即中断
  语义合取 = 18/18 通过）；`test_tools.sh` 的 `TOOLS_TESTS_WITH_INPUT` 为空，
  3 个程序直接运行；`test_vmdkinfo.sh` 顶层 `if ! test -d input → exit 77`。
- **唯一 SKIP**：`test_vmdkinfo.sh` 需要 `tests/input/` 夹具，发布用 orig
  tarball 不含该目录（`tar tzf … | grep -c '/tests/input/'` = 0），按上游规则
  `exit 77` → automake 记为 `SKIP`（`.trs` 逐字：`test-result: SKIP`）。
- `TESTS` 内条件项 `test_python_module.sh`（`if HAVE_PYTHON_TESTS`）因
  `--disable-python` 不成立，未进入注册面，**不计入 N**；`check_SCRIPTS`
  （test_runner.sh、test_manpage.sh、pysmraw 式 py 支撑等）是支撑脚本而非
  注册项，亦不混入（`test_manpage.sh` 在本版本就不在 `TESTS` 里）。
- **上游 HEAD 下界独立复核**（2026-09-25 浅稀疏克隆）：`refs/heads/main` =
  `496944fabbf5cfe32fb1ff19bfe62678b7ad566f` 的 `tests/Makefile.am`：
  `check_PROGRAMS` **同为这 21 个（名字集合与本版逐字一致，diff 为空）**；
  入口注册面已重构为 autotest（`check_AUTOTESTS` = test_library /
  test_manpages / test_tools 3 项 + python 条件项）——**注册面项数 3+21=24
  与本版持平**，声明 N 不低于审方独立清点下界。HEAD 另有 `*.at` 内
  `AT_SETUP` 行 19 条，属 autotest 用例粒度（与注册面不同口径，不混用、
  不采用；本版本 tarball 无 autotest 结构）。
- 上游 HEAD 相对本版的入口差异：HEAD 用 `test_manpages` 替代了本版
  `test_vmdkinfo.sh` 的位置（本版 `test_manpage.sh` 在 check_SCRIPTS 中），
  属上游测试框架迁移，不影响本版注册面清点。

## 消费者测试（`test_package/`，Conan L1）

- `test_libvmdk.c`（**41 项断言**）：版本串（`libvmdk_get_version()` =
  上游 20240510，非 Conan ref）、access flags、codepage 正常/错误（-42）/
  UTF-8（0）三路、VMDK 签名探测正（descriptor）反（flat 数据文件）错
  （缺失文件）三路、**合成 monolithicFlat VMDK**（描述文件 + 8 KiB flat
  extent 由测试自身 POSIX 写盘）全链路：open → open_extent_data_files →
  media size 8192 → disk type MONOLITHIC_FLAT → CID 0xfffffffe /
  parentCID 0xffffffff → 全量读回比对 → 跨扇区读 → seek/get_offset →
  **EOF 语义（读到头返 0 字节且不置错）** → 错误路径（缺失文件 open=-1 +
  错误回溯可打印）→ 生命周期（signal_abort / close=0 / free）。
- `test_ohos.c`（**31 项断言**，仅 OHOS 编译运行）：`__OHOS__` 编译目标、
  TMPDIR 语义（设置/非只读 /tmp/可写）、**在 TMPDIR 下合成 monolithicFlat
  VMDK 并读回全链路**（含跨扇区边界 16 字节读 504..519、尾部 64 字节读
  8128..8191、open **之前**设置 max open handles、signal_abort、缺失文件
  错误回溯）。
- `vmdkinfo -V`：安装后的 CLI 产物加载共享库并输出版本串（运行/加载验证，
  test() 内执行）。
- 两程序断言合计 **72**；编译期 `clang -Wall -Wextra` 零告警，本地对原生
  构建树实跑 41/41 与 31/31 全 PASS（与 conan create 干净轮读数一致）。
- **合成夹具的两个上游语义坑（探针实测，DRAFT-E726）**：
  ① `createType` 必须用 VMDK 规范 camelCase `monolithicFlat`（解析器按
  value_length 分支只认 14 字符 `monolithicFlat`；带空格的 VMware 风格
  `monolithic flat` 能解析元数据但 disk_type 留 UNDEFINED → extent 表初始化
  报 `unsupported disk type`）；
  ② `libvmdk_handle_open()` 对 monolithic flat **不会**自动打开 extent 数据
  文件（读操作报 `missing extent data file IO pool`），必须显式调用
  `libvmdk_handle_open_extent_data_files()`；
  ③ `libvmdk_handle_set_maximum_number_of_open_handles()` 只能在 open 之前
  （pool 未建）调用才返 1；pool 已建时恒返 -1 且破坏 pool 的 last-used
  list（后续 close 也连带失败）——上游 libvmdk→libbfio 包装条件疑似写反
  （`!= -1` 分支把成功返回当失败），已在测试注释与 DRAFT-E726 登记。

## 语言预检（R47）

`lang-preflight libvmdk 20240510 --src <发行 tarball 解包根>`（OHPCD_LANG=c）
**首跑即过**：`detected=cpp`（autotools 构建入口，主体纯 C，c↔cpp 兼容族），
milestone=lang_checked。同族 libsmraw 首跑 `mixed→env_unsupported` 的根级
绑定打包元数据假阳性（DRAFT-E586 家族）在本包**未复现**（工具的绑定目录
排除规则已覆盖 pyvmdk/ 形态）。

## 已知限制

1. `vmdkmount` 的 FUSE 挂载功能：OHOS/CI 无 libfuse（`checking for
   fuse.h... no`），`AX_LIBFUSE_CHECK_ENABLE` 探测为否，mount 路径按上游
   `#if defined(HAVE_LIBFUSE)` 守卫**编译期降级**（工具本体与 `-V` 不受
   影响；同族 libsmraw smrawmount 同口径）。`vmdkinfo` 全功能不受影响。
2. `test_vmdkinfo.sh` 工具级端到端依赖上游 `tests/input/` 夹具（发布包
   不含），按上游规则 SKIP——替代验证：① 上游 `vmdk_test_tools_info_handle`
   单元测试真实执行通过；② 消费者测试以合成 VMDK 覆盖 info 面（media
   size/disk type/CID 读回）；③ `test()` 内 `vmdkinfo -V` 加载验证。
3. `libvmdk_handle_set_maximum_number_of_open_handles()` 的 pool 已建分支
   上游缺陷（恒 -1 + 污染 pool），见 DRAFT-E726；测试按「open 前调用」的
   正确姿势规避，缺陷本身未修（不改上游源码，已登记）。
4. CI 探针长选项：libyal 工具只接受短选项 `-V`/`-h`（`--version` 会 rc=1），
   与 libsmraw L2 skip 同型；产物加载由 test_package 的 `vmdkinfo -V`
   （conanrun 环境）单独覆盖。
