# libvsgpt 0-20240504 适配笔记

## 状态

- 状态：built（真机 W3 `conan create` + 上游 `make check` + `test_package` 均真实执行）
- 分支：`feat/libvsgpt-0-20240504`；包目录：`archives/l/libvsgpt/0-20240504/`
- 构建系统：autotools（上游自带生成的 `configure`，无需自举；设备与 CI worker 都不需要 automake/autoconf）
- 编译器：clang 15.0.4（OHOS SDK，`/data/service/hnp/bin/clang`），目标 `aarch64-unknown-linux-gnu`
- 交付物：共享库 `libvsgpt.so.1.0.0`（+ `libvsgpt.so.1`、`libvsgpt.so`）、`include/libvsgpt.h` 与
  `include/libvsgpt/*.h`、`bin/vsgptinfo`、`lib/pkgconfig/libvsgpt.pc`、`licenses/COPYING*`

## 源码溯源（版本号为何是 `0-20240504`）

- 上游项目：`https://github.com/libyal/libvsgpt`；本包版本 `0-20240504` 对应上游 2024-05-04 快照。
- **上游未发布该版本的 release 资产**（设备实测 2026-09-20）：

```sh
$ git ls-remote --tags https://github.com/libyal/libvsgpt.git
e7ca53cbaa89d5288bb54201308dfe01f837ff00	refs/tags/20260731
88354d5c6dec247cda81df969ba7973f907dfc9e	refs/tags/20260911
$ curl -sS -o /dev/null -w '%{http_code}\n' -I -L \
    "https://github.com/libyal/libvsgpt/releases/download/20240504/libvsgpt-experimental-20240504.tar.gz"
404
```

  Releases API 只返回 `20260731`、`20260911` 两个 tag（无 20240504）。
- 因此使用权威发行版归档（Debian pool）的 pristine orig tarball，并用 Debian 源包
  **PGP 签名 .dsc** 的 `Checksums-Sha256` 锚定内容：

```sh
$ curl -sS -o libvsgpt_0~20240504.orig.tar.gz \
    "https://deb.debian.org/debian/pool/main/libv/libvsgpt/libvsgpt_0~20240504.orig.tar.gz"
$ sha256sum libvsgpt_0~20240504.orig.tar.gz
60e8239d29c7f1a43282a96d86e82e147c3b87a4aa343db73be2870c465c6ac9   # 1510764 字节
$ curl -sS "https://deb.debian.org/debian/pool/main/libv/libvsgpt/libvsgpt_0~20240504-2.dsc" | grep -A2 Checksums-Sha256
 60e8239d29c7f1a43282a96d86e82e147c3b87a4aa343db73be2870c465c6ac9 1510764 libvsgpt_0~20240504.orig.tar.gz
```

  `.dsc` 声明的 `Version: 0~20240504-2`（Debian 用 `~` 表示上游无正式版本号），
  Conan 版本号按本仓库既有的 `0-<日期>` 口径写作 `0-20240504`（同族先例
  `archives/l/lib1305/0-20250415`、`archives/l/lib25519/0-20260614`；同批在办任务 libfsfat 0-20260208 同口径）。
- tarball 顶层目录为 `libvsgpt-20240504/`（`strip_root=True` 直接命中），内部自带
  `configure`、`aclocal.m4`、`config.guess`（timestamp 2023-06-23）、`config.sub`（同 2023-06-23）、
  `Makefile.in` 等生成文件，以及 13 个 standalone libyal 组件目录
  （libbfio libcdata libcerror libcfile libclocale libcnotify libcpath libcsplit
  libcthreads libfcache libfdata libfguid libuna）。
- 源码规模（设备实测 `find | wc -l`）：`.c` 201、`.h` 321、`.cc` 2（`ossfuzz/*_fuzzer.cc`）、
  `.py` 4（`setup.py` + 3 个 `tests/pyvsgpt_test_*.py`）、`.sh` 7（`tests/` 下 6 个
  `test_*.sh` + 顶层 `ltmain.sh`）。

## W0 依赖发布检查：无外部依赖（none）

三条独立证据（任务侧 `w0-deps.txt` 记 `none`）：

1. `configure.ac` 全文无 `PKG_CHECK_MODULES`、无 `AC_CHECK_LIB`；只有
   `AC_CHECK_HEADERS([stdarg.h varargs.h])`（系统头）与 `AX_PYTHON_CHECK_ENABLE`
   （配方已 `--disable-python`）。
2. 13 个 libyal 组件以 standalone 形式内嵌在发布包内（`AX_LIB*_CHECK_ENABLE` 宏，
   `m4/*.m4` + `Makefile.am` 的 `SUBDIRS` 树内构建）。
3. Debian 源包 `Build-Depends: dpkg-dev, debhelper-compat, dh-python, pkgconf,
   python3-dev, python3-setuptools` —— 无任何 libyal 二进制开发包依赖。

本版本**没有** libfuse/`vsgptmount`（`configure.ac` 无 fuse 检查、`vsgpttools/Makefile.am`
的 `bin_PROGRAMS` 只有 `vsgptinfo`），故配方不需要 `--with-libfuse=no`；python 绑定
（`pyvsgpt`）显式 `--disable-python`。

## 构建步骤（配方实际序列）

```sh
# build() 内（OHOS）：CONFIG_SHELL=/data/service/hnp/bin/bash
# 1) configure 内 2 处 `umask 077` → `022`（HMDFS，见平台适配表）
"$CONFIG_SHELL" ./configure \
    --prefix=<pkg> --bindir=<pkg>/bin --libdir=<pkg>/lib --includedir=<pkg>/include \
    --enable-shared --disable-static --disable-python --enable-static-executables=no \
    --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu
make -j<n>                                                  # n 显式钉为 2
make -j<n> check LOG_COMPILER=/data/service/hnp/bin/bash     # 上游测试，见下
make install DESTDIR=<pkg>                                  # package() 内，cwd=源码目录
```

设备原生（不经 Conan）复核同一序列：`configure` rc=0 / `make -j2` rc=0 /
`make -j2 check` rc=0 / `make install` rc=0（日志 `$TASK_DIR/native-build.out`，
脚本 `$TASK_DIR/native-build.sh`）。

## 平台适配（全部内联在 `conanfile.py build()`，无 `patches/` 文件）

| # | 现象 | 根因 | 处置 |
|---|------|------|------|
| 1 | configure 阶段 `config.guess` 报 `can't create …/dummy.c: Permission denied` | `configure` 内 2 处 `umask 077`；HMDFS 上按 077 建出的 0700 临时目录连创建者都无法写入（E011 同族实测） | 只把源码树的 2 处 `umask 077` 改为 `022`，并让整个构建过程保持 `umask 022`；`config.status` 由改写后的 configure 生成，实测无需二次替换 |
| 2 | `./configure` 报 `cannot guess build type` / 三元组不识别 | 随包 `config.guess`/`config.sub`（timestamp 2023-06-23）不识别 HarmonyOS；**本版本 `config.sub` 也不接受 `linux-ohos`** | 实测 `./config.sub aarch64-unknown-linux-ohos` → `Invalid configuration … OS 'ohos' not recognized`，而 `aarch64-unknown-linux-gnu` 正常；OHOS 下用 `update_configure_args()` 显式给 `--build/--host=aarch64-unknown-linux-gnu`（替换语义，避免与 `AutotoolsToolchain` 重复），**不改** `config.guess`/`config.sub`；libtool 正常产出 `libvsgpt.so.1.0.0`（SONAME `libvsgpt.so.1`） |
| 3 | HMDFS 上直接执行源码树脚本受限 | 设备对脚本执行/临时目录语义受限 | OHOS 下用 profile `[buildenv]` 注入的 `CONFIG_SHELL=/data/service/hnp/bin/bash` 显式启动 `configure`；`make check` 的 `TESTS` 入口同为 bash 脚本，用 automake 的 `LOG_COMPILER` 指定同一解释器 |
| 4 | 测试程序需要读回构建树内的共享库 | `make check` 在树内运行未安装的库 | 仅在本进程子树内把 `libvsgpt/.libs` 前置进 `LD_LIBRARY_PATH`，退出时还原原值 |

**R6 声明（如实登记，唯一例外）**：本包**不修改**上游任何 C/H 源文件、测试脚本、`Makefile.am`，
也不新增 `patches/` 补丁文件；唯一的**生成脚本**改动是上表第 1 行的 `configure` 内 2 处
`umask 077`→`022`（在 Conan 缓存内的源码副本上执行，不改动仓库内任何文件）。这是 E011 的既有
处置口径，同族先例采用同一做法（`archives/l/libesedb/20240420` 的 `patches/0004-configure.patch`、
libfsntfs 20251028 的 `build()`；同批在办任务 libfsfat 0-20260208 亦同口径）。

**关于上游 `tests/test_runner.sh`（不需要改写，与同族早期先例不同）**：该文件用
`file -b` 输出里是否含字面量 `POSIX shell script` 判断「测试程序是不是 libtool 包装脚本」，
而 OHOS 的 `file` 输出形如 `/bin/sh script`（设备实测），判定因此不成立、测试直接执行
libtool 包装脚本本身。设备原生实测 `make check` 全绿（20 个 C 测试程序全部 PASS），
故**没有**像 libfsntfs 20251028 那样在 `build()` 内改写 `test_runner.sh`。

**原生探索的一个伪影（不属配方问题，如实登记）**：首次用 `cp -r` 复制源码树做原生复核时，
所有文件被刷成同一 mtime，automake 判 `Makefile.in` 过期并触发维护者模式重建，报
`automake-1.16: inaccessible or not found` / `make: *** [Makefile:641: Makefile.in] Error 1`。
设备实际是 automake 1.19（tarball 的 `missing` 脚本按 1.16 命名查找）。改用 `cp -a`
保留 tarball 内时间戳（`Makefile.am` 12:31 < `Makefile.in` 12:44）后 make rc=0；
conan 的 `get()` 解包本就保留 mtime，配方侧不受影响。完整判据见知识草稿 E591。

## 上游测试（`make check`，构建期在 build() 内执行）

清点口径 = `tests/Makefile.am` 的**两个 automake 注册面**：

| 注册面 | 数量 | 本包实测 |
|---|---|---|
| `TESTS`（shell 入口脚本） | 3 | `PASS 2`（test_library.sh、test_tools.sh）＋ `SKIP 1`（test_vsgptinfo.sh） |
| `check_PROGRAMS`（C 测试程序） | 20 | 全部真实执行、`PASS 20` |
| **合计（N）** | **23** | `PASS 22` / `SKIP 1` / `FAIL 0` |

- `check_PROGRAMS` 20 个：boot_record、checksum、chs_address、error、io_handle、
  mbr_partition_entry、mbr_partition_type、notify、partition、partition_entry、
  partition_table_header、partition_type_identifier、partition_values、section_values、
  sector_data、support、tools_info_handle、tools_output、tools_signal、volume。
- 其中 17 个由 `test_library.sh` 驱动（`LIBRARY_TESTS` 15 个 + `LIBRARY_TESTS_WITH_INPUT`
  的 support、volume），3 个由 `test_tools.sh` 驱动（info_handle、output、signal）。
- **`support`/`volume` 不是跳过**：`test_library.sh` 在 `tests/input/` 缺失时按上游逻辑
  退化为无输入运行（脚本内的 `if test -d "input"` 分支），设备实测两者都真实执行并 PASS。
- `tests/Makefile.am` 的 `TESTS` 还含条件项 `test_python_module.sh`（`if HAVE_PYTHON_TESTS`）；
  本包 `--disable-python`，该条件不成立，故未进入 `TESTS`，**不计入 N**（不同口径不混用）。
  `check_SCRIPTS` 的 9 项（3 个 `pyvsgpt_test_*.py` + 6 个 shell 脚本，含被 runner `source`
  复用的 `test_runner.sh`）是测试支撑脚本，不是注册项，亦不混入。
- **唯一 SKIP**：`test_vsgptinfo.sh` 需要 `tests/input/` 夹具，而发布用 orig tarball
  不含该目录（`tar tzf … | grep -c '/input/'` = 0），脚本按上游规则 `exit 77` →
  automake 记为 `SKIP`。原始读数（设备原生轮，`tests/test-suite.log` 逐字）：

```text
=============================================
   libvsgpt 20240504: tests/test-suite.log
=============================================

# TOTAL: 3
# PASS:  2
# SKIP:  1
# XFAIL: 0
# FAIL:  0
# XPASS: 0
# ERROR: 0

SKIP: test_vsgptinfo.sh
=======================

Test input directory not found.
SKIP test_vsgptinfo.sh (exit status: 77)
```

```text
# tests/test_library.sh.log
Testing: boot_record (PASS)
Testing: checksum (PASS)
Testing: chs_address (PASS)
Testing: error (PASS)
Testing: io_handle (PASS)
Testing: mbr_partition_entry (PASS)
Testing: mbr_partition_type (PASS)
Testing: notify (PASS)
Testing: partition (PASS)
Testing: partition_entry (PASS)
Testing: partition_table_header (PASS)
Testing: partition_type_identifier (PASS)
Testing: partition_values (PASS)
Testing: section_values (PASS)
Testing: sector_data (PASS)
Testing: support (PASS)
Testing: volume (PASS)
PASS test_library.sh (exit status: 0)
```

```text
# tests/test_tools.sh.log
Testing: info_handle (PASS)
Testing: output (PASS)
Testing: signal (PASS)
PASS test_tools.sh (exit status: 0)
```

- 覆盖面：CRC-32 与弱 CRC-32 校验（`libvsgpt_checksum`）、GPT 头与分区表项解析、
  MBR 分区项与 CHS 地址、分区句柄读写与 seek、volume 生命周期，均由上述 C 程序真实执行覆盖。

## 消费者测试（`test_package/`，Conan L1）

| 文件 | 平台 | 断言数 | 内容 |
|---|---|---|---|
| `test_libvsgpt.c` | 全部 | 16 | 版本串、读/读写访问标志、codepage 正常路径、`check_volume_signature` 的 0（无 GPT 签名）与 -1（文件不存在）路径、`volume_open` 错误路径 + 错误对象、volume 生命周期释放 |
| `test_ohos.c` | OHOS | 28 | `__OHOS__` 编译目标、TMPDIR 语义（存在、非 `/tmp`、可写）、**合成合法 GPT 磁盘镜像读回链路**：写盘生成 2 MiB 镜像（保护性 MBR + 主 GPT 头 + 主 entries + 备 entries + 备头，CRC-32 全部正确）、签名检测、打开、512 B 扇区、分区数、磁盘 GUID、entry index 查询（`has_partition_with_identifier`/`get_partition_by_identifier`）、分区 GUID 与类型 GUID、卷内字节偏移、分区大小、读回 marker 与填充图案、当前偏移推进、关闭释放、镜像清理 |

合计 **44 项断言**（`test_package/MANIFEST.yml` 的 `assertion_count`）。镜像由测试自身用纯
POSIX 写盘生成，不依赖任何外部夹具，因此这条链路在 CI 与设备上都能真实执行。另外 `test()` 内
还执行安装后的 `bin/vsgptinfo -V` 并要求输出含 `20240504`，验证 CLI 产物能加载共享库
（运行/加载验证）。

**四处公开 API 的反直觉约定**（消费者测试按实测值断言，避免"想当然"的假绿；首轮实测撞中其中两处）：

1. `libvsgpt_volume_get_partition_by_identifier()` / `libvsgpt_volume_has_partition_with_identifier()`
   的第二个参数是 **`uint32_t entry_index`**（源码注释逐字："corresponding (partition) entry index"），
   **不是 GUID**；按名字传 GUID 会编译失败或查不到条目。
2. `libvsgpt_partition_get_offset()` 返回**分区内当前读偏移**（初值 0，读完一扇区为 512）；
   卷内字节偏移要用 `libvsgpt_partition_get_volume_offset()`（首轮按名字误解，实测该断言 FAIL 后修正）。
3. `libvsgpt_volume_close()` **成功返回 0**（头文件注明 "Returns 0 if successful or -1 on error"）。
4. `libvsgpt_get_version()` 返回**上游版本串 `20240504`**，不是本包的 Conan 版本 `0-20240504`。

**合成 GPT 夹具的实测口径**：`volume_open()` 会同时读主/备两个 GPT 头并逐字段比对
（header/backup block number 互为镜像、area start/end、disk identifier、entries 数/大小/CRC），
主头 `is_corrupt` 才回退备头、两个都 corrupt 直接失败；头 `is_corrupt` 判据为
`stored_checksum != 0 && stored_checksum != calculated` 或 `major != 1 || minor != 0`。
本测试用标准 reflected CRC-32（poly `0xEDB88320`）计算前 92 字节（校验和字段置 0）的校验和，
主备两套结构都写全，实测 `is_corrupt` 为 0、读回链路全部通过。

## 设备原生验证（不经 Conan 的独立复核）

```sh
$ sh "$TASK_DIR/native-build.sh"
== [1] E011：configure 内 2 处 umask 077 -> 022（仅构建副本） ==   # before=2 after=0
== [2] config.sub 三元组核对 ==
aarch64-unknown-linux-gnu                                        # 接受
Invalid configuration 'aarch64-unknown-linux-ohos': OS 'ohos' not recognized   # 拒绝
== [3] configure ==                                              # configure rc=0
== [4] make -j2 ==                                               # make rc=0
== [5] make check（沙箱 HOME，LOG_COMPILER 指定 bash） ==          # make check rc=0
== [7] make install DESTDIR ==                                   # install rc=0
```

```sh
# 消费者测试对「已安装」产物（DESTDIR staging prefix）编译并运行
$ clang test_libvsgpt.c -o probe_generic -I<prefix>/include -L<prefix>/lib -lvsgpt
$ clang test_ohos.c     -o probe_ohos     -I<prefix>/include -L<prefix>/lib -lvsgpt
$ LD_LIBRARY_PATH=<prefix>/lib ./probe_generic
16 assertions passed
$ LD_LIBRARY_PATH=<prefix>/lib TMPDIR=<writable> ./probe_ohos
28 assertions passed (GPT image round trip under TMPDIR)
$ LD_LIBRARY_PATH=<prefix>/lib <prefix>/bin/vsgptinfo -V
vsgptinfo 20240504
```

（一键复现：`sh "$TASK_DIR/triplet-and-gpt-probe.sh"`，同时打印 `config.sub` 两个三元组的
实测读数与两条消费者链路的断言计数。）

## 语言预检（R47）与工具侧误判

`lang-preflight` 对本包判 `detected_language=mixed` → 终态 `env_unsupported`，**判据不成立**：
包主体是 C（201 个 `.c` / 321 个 `.h`，工具自报 c 占 97%，autotools `configure` 为真实构建入口），
命中 `manifest=python` 的 `pyproject.toml`/`setup.py`/`setup.cfg` 是**可选 Python 绑定模块
（`pyvsgpt`）的打包元数据**（`pyproject.toml` 全文只有 3 行 setuptools 后端声明，
`setup.cfg` 自述 `description = Python bindings module for libvsgpt`，`setup.py` 首行
`Script to build and install Python-bindings`），且配方已 `--disable-python`。
该步在编排中按 `--skip-step lang-preflight --start-note "<理由>"` 记为**未执行**（不是通过）。
本批 libyal 家族第 4 次独立复现（libfsxfs、libfvde、libfsfat 之后），根因与处置见知识草稿 E586；
`feedback/pending/2026-09-20-libvsgpt-0-20240504.md` 另登记本任务观测。

## W4 独立审计（首轮）与逐条处置

被审 SHA `d637e5e8d63ba54d6a9cad1333b038c7e27ce5a4`（结论 `head_sha` 与 `git rev-parse HEAD`
逐字一致）；`verdict=pass`、P0=0、P1=0、P2=1、P3=4。结论文件 `reports/audit-result.json`
（sha256 `6b76d1eaba8e82433b0baa6e127fde35c2d6f1574c9c3cf0f01b7d1ad003630b`，位于 `.gitignore`
的 `reports/` 规则内，不进提交面）。5 条问题逐条处置：

| 级别 | 问题 | 处置 |
|---|---|---|
| P2 | `config.guess` 世代写成 `2024-07-27`，独立实测为 `timestamp='2023-06-23'`（该值实为兄弟任务 libfsfat 0-20260208 的读数，属照抄未复测） | 已把 6 个被跟踪位置（`conanfile.py`、`notes.md` ×2、`manifest.yaml`、`README.md`、草稿 `.kv`）与草稿 `.md` 改为实测值；草稿第 1 节的判据改以 `config.sub` 世代为准（本包 `2023-06-23` 拒绝 / libfsfat `2024-05-27` 接受），并补上取值命令与逐字读数 |
| P3 | `check_SCRIPTS`「8 个」与实物不符，实为 9 项 | 已改为「9 项（3 个 `pyvsgpt_test_*.py` + 6 个 shell 脚本）」 |
| P3 | R6 字面口径：`build()` 就地改写生成脚本 `configure` 的 2 处 `umask` | 维持现状（审计给出的选项①）：提交面 13 个新增文件中无任何被改写的生成文件，已在本文「R6 声明」与 `manifest.yaml` 显式登记，先例真实（libesedb 20240420 的 `patches/0004-configure.patch`、libfsntfs 20251028 的 `build()` 同形代码、E011 的推荐方案即此）；PR 正文继续显式援引 |
| P3 | 草稿 `rec_command` 中文说明粘连致不可直接执行 | 已把说明移出 `rec_command`（并入 `rec_description`），`rec_command` 只保留可直接执行的一行 |
| P3 | PR 正文两处 `<待填>`（关联 Issue、W4 结论） | 建 PR 前回填（Issue 编号在创建后回写；W4 结论按本节转述） |

> 上述修改中 `conanfile.py` 的 docstring 变更会让 recipe revision 前移，按
> `tools/delta_class.py` 的判据属 **T3**（`conanfile.py`、`manifest.yaml`、`notes.md`、`README.md`、
> 草稿 `.kv`/`.md`，取最高级），故未以"只是注释"为由跳过——按纪律重跑采信轮
> （干净轮，构建标志计数 `{'run_make': 9, 'calling_build': 2, 'apply_patch': 0}`）并重新生成
> 审计输入派复审。

### 二轮审计（被审 SHA `5217a3a61d4d62c392bee0457e74fb301f451582`）

`verdict=pass`、P0=0、P1=0、P2=0、P3=6；结论文件 `reports/audit-result.json`
（sha256 `ee29dffd71508eaf21e6cec01ec99461abf038a92308411a583102912ccbf656`）。6 条 P3 逐条处置：

| 级别 | 问题 | 处置 |
|---|---|---|
| P3 | 探针脚本横幅仍印旧值 `config.guess 2024-07-27` | 已改为 `config.guess/config.sub timestamp 均为 2023-06-23`（任务目录脚本，不进提交面） |
| P3 | 草稿 `error_signature` 第 5 分支含一次性随机 mktemp 路径（engine 字面匹配永不命中） | 已改为真实报错的稳定片段 `dummy.c: Permission denied`，并在 note 里说明省略的是随机目录名 |
| P3 | 本文源码规模注解 `.sh 7（tests/*.sh）` 与实物不符 | 已改为「`tests/` 下 6 个 `test_*.sh` + 顶层 `ltmain.sh`」 |
| P3 | R6 字面张力 | 维持选项①（同首轮处置；先例与登记均在） |
| P3 | PR 正文两处 `<待填>` | 建 PR 前回填（W4 结论按本节转述；Issue 编号在建 Issue 后回写） |
| P3 | `manifest.yaml` 三条 `# knowledge_ref: DRAFT-E586-…` 在 `upstream/main` 无对应物 | 保留：该草稿由同批 libfsfat 任务的在办 PR（!11250）携带，条目内容确属 E586 范围；不改指 E591（会失真）。已在最终汇报中作为已知非阻断项列出 |

> 本轮的 `notes.md` 与草稿 `.kv` 修改属 **T1**（`tools/delta_class.py` 判「免设备重验、免 W4 复审」），
> 但为避免 H11「审计结论 `head_sha` ↔ HEAD」失配，仍按下述方式做**增量**复核。

### 三轮审计（被审 SHA `c642f6560dc530d9004501ba553bbbbad71f1508`）

`verdict=pass`、P0=0、P1=0、P2=4、P3=2；结论文件 `reports/audit-result.json`
（sha256 `15e9482004bf32d033dfafdaf62ac9d02389eaa388a0494c63707143c4c4e08f`）。
本轮审计独立补做了「审方口径的上游 HEAD 下界」清点：`git ls-remote` 的 HEAD
`f3ebbf95068801409f947e046ff6b0d36197bb17` 的 `tests/Makefile.am` 为
`check_PROGRAMS` 20 + `check_AUTOTESTS` 3 = 23（名字集合与本版本一致）→ 声明 N=23 无少报。
其 4 条 P2 与 2 条 P3 的处置：

| 级别 | 问题 | 处置 |
|---|---|---|
| P2 | PR 正文两处 `<待填>`（机械闸不拦） | 建 PR 前回填（W4 结论按本段转述；Issue 编号在建 Issue 后回写） |
| P2 | PR 正文称「上游 HEAD 无法按本版本之外的注册面复核」不成立 | 已改为**实测读数**：上游 HEAD `f3ebbf95…` 的注册面 20 + 3 = 23（本任务自行 `curl` 拉取该 SHA 的 `tests/Makefile.am` 复核），并把 24 个 `vsgpt_test_*.c` 中 4 个支撑源与 `VSGPT_TEST_RUN`=73 的排除口径一并写明 |
| P2 | 草稿 `.md` 把 `libvsgpt_partition_get_offset()` 写成「字节偏移（LBA × bytes_per_sector）」 | 已更正为「返回**分区内当前读偏移**（初值 0，读完一扇区 512）」，并单列 `libvsgpt_partition_get_volume_offset()`（卷内字节偏移）与 `get_size()`（字节）两行，消除与 `.kv`/`manifest.yaml`/正文的矛盾 |
| P2 | 路径 B Issue 正文模板仍写 `config.guess 2024-07-27` | 已改为实测值 `2023-06-23`（并给 libfsfat 的 `config.sub` 补上 `2024-05-27` 世代） |
| P3 | 正文/本文把 `archives/l/libbfio/20170123`、`archives/l/libfsfat/0-20260208` 当**已合入先例**引用（二者在办） | 已改为已合入的 `libfsntfs/20251028`、`libesedb/20240420`、`lib1305/0-20250415`；libfsfat 仅作为**同批在办任务**的数据对照保留（其 `config.sub` 世代读数仍是草稿第 1 节的反例来源） |
| P3 | 收尾汇报仍写上一轮 SHA | 收尾时以 `report_final.py --emit` 重新生成，写入最终 SHA |

> 本轮处置再次触及 `notes.md` 与草稿 `.md`（均为 T1 文档物料，不涉及构建输入与门禁物料），
> 按 §3.3 不重跑设备验证；因 H11 要求审计 `head_sha` 与 HEAD 逐字一致，故对最终 tip 做一次
> **增量** W4 复核（仅审这些文档 delta 与全量提交面），并在最终汇报中单列审计轮次与理由。

## 已知限制

1. `test_vsgptinfo.sh`（1/23）在上游发布包缺少 `tests/input/` 夹具时按上游规则 SKIP，
   非失败；GPT/MBR 解析路径由 20 个 `check_PROGRAMS` 与 `test_ohos.c` 的合成 GPT 镜像
   读回链路覆盖。
2. `test_python_module.sh` 只在 `--enable-python` 时进入 `TESTS`（本包显式关闭），未运行；
   python 绑定 `pyvsgpt` 不在交付面内。
3. 原生探索首次 `cp -r` 造成的 `automake-1.16` 伪影已排除（改用 `cp -a`），与配方无关。
