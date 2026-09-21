# libsmraw 20240506 适配笔记

## 编译环境

- 构建系统: autotools（Debian pristine orig tarball 自带预生成 configure）
- 编译日期: 2026-09-20
- 编译器: clang 15.0.4（OHOS 工具链，CC 无裸 `cc`）
- 状态: built

## 源码溯源（2026-09-20 实测）

1. 上游 GitHub（libyal/libsmraw）`git ls-remote --tags` 返回两个 tag：
   `refs/tags/20240506`（commit `995b9e200ae8c836439f14741253143803fecb0c`）与
   `refs/tags/20260902`。任务卡版本 20240506 对应的 tag **存在**。
2. 但该 tag 的 release 资产
   `https://github.com/libyal/libsmraw/releases/download/20240506/libsmraw-experimental-20240506.tar.gz`
   实测 **404**（响应体 `Not Found`，9 字节；同族 libfsapfs/libfvde 的 release
   资产是存在的，libsmraw 没有发布 release 资产）。
3. 故使用权威发行版归档的 pristine orig tarball
   `https://deb.debian.org/debian/pool/main/libs/libsmraw/libsmraw_20240506.orig.tar.gz`：
   sha256 `1d928be52646d4e8283e452824c1839b0f844438848efe7888cc2c5613d12d58`
   （1660152 字节）与 PGP 签名的 `libsmraw_20240506-2.dsc` 的
   Checksums-Sha256 **逐字一致**（.dsc 含 `BEGIN PGP SIGNATURE` 计数 = 1，
   源版本 20240506-2）。
4. tarball 顶层目录 `libsmraw-20240506`，含预生成 `configure`/`Makefile.in`/
   `config.guess`/`config.sub`（无需 autoreconf——这点对 CI 关键：worker PATH
   没有 automake）。

## W0 依赖发布检查：无外部依赖（none）

三条独立证据（任务侧 `w0-deps.txt` 记 `none`，无需 conan install 验证空集）：

1. `configure.ac` 无 `PKG_CHECK_MODULES`、无外部 `AC_CHECK_LIB`；libyal 组件以
   standalone 宏（`AX_LIB*_CHECK_ENABLE`）树内构建。
2. 14 个 libyal 组件以 standalone 形式内嵌在发布包内：`libbfio libcerror libcdata
   libcfile libclocale libcnotify libcpath libcsplit libcthreads libfcache libfdata
   libfvalue libhmac libuna`（另有顶层 common/ 共享支撑代码，不计入组件数），
   `--with-libbfio` 不给 DIR 时用内嵌副本。
3. Debian 源包 `Build-Depends: dpkg-dev, debhelper-compat (= 13), dh-python, pkgconf,
   python3-dev, python3-setuptools, libfuse3-dev`——无任何 libyal 二进制开发包；
   libfuse3-dev 仅 Debian 打包侧启用 smrawmount 的 FUSE 挂载，本配方不带（OHOS/CI
   无 libfuse，`AX_LIBFUSE_CHECK_ENABLE` 自动探测为否，smrawmount 仍按上游默认构建，
   挂载功能编译期降级，见「已知限制」）。

## 编译步骤（配方实际序列）

conanfile.py `build()` 内（OHOS 分支）：

1. `os.umask(0o022)` 全程保持 022；
2. `_patch_hmdfs_umask()`：随包 configure 内 2 处 `umask 077` → `umask 022`（E011，
   HMDFS 上 0700 临时目录连创建者都不可写）；
3. `CONFIG_SHELL=/data/service/hnp/bin/bash`（profile [buildenv] 注入）显式启动
   configure，参数由 AutotoolsToolchain 统一构造：
   `--enable-shared --disable-static --disable-python --enable-static-executables=no
   --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`；
4. `make -j2`（显式限并发：os.cpu_count()=20 而 affinity=8，默认会 2.5× 超订）；
5. `make -j2 check LOG_COMPILER="<bash>"`，进程子树内临时把
   `libsmraw/.libs` 前置进 `LD_LIBRARY_PATH`（测试程序读回树内共享库），退出还原。

`package()`：`make install DESTDIR=<pkg>` + 删除 `lib/*.la` + 拷贝
`COPYING`/`COPYING.LESSER` 到 `licenses/`。

## 平台适配（全部内联在 `conanfile.py build()`，无 `patches/` 文件）

| # | 事实 | 依据 |
|---|------|------|
| 1 | E011：configure 内 2 处 `umask 077` → `022`，全程 umask 022 | HMDFS 目录模式落盘后不可改（0700 连创建者不可写），同族 libvsgpt/libfsapfs 同口径 |
| 2 | 三元组：`--build/--host=aarch64-unknown-linux-gnu`（update_configure_args 替换语义） | 随包 config.sub（2023-06-23 vintage）不识别 `linux-ohos`；同族 libvsgpt 0-20240504 设备实测 `Invalid configuration ... OS 'ohos' not recognized`，本版本未单独复测该报错（同 vintage 先例采信），conan create 干净轮全绿即证参数有效 |
| 3 | `CONFIG_SHELL` 指向绝对路径 bash 启动 configure；make check 用 `LOG_COMPILER` 指定同一 bash | OHOS 无 `/bin/bash`，`/bin/sh` 是 toybox；libyal TESTS 全是 bash 脚本 |
| 4 | 测试程序运行期把 `libsmraw/.libs` 前置进 `LD_LIBRARY_PATH`（只作用本进程子树） | 共享库模式下 automake 测试需要读回树内 libsmraw.so |
| 5 | `--disable-python` | pysmraw 绑定不入交付面；`HAVE_PYTHON_TESTS` 条件不成立，`test_python_module.sh` 不进 TESTS（不计入上游 N） |

## 上游测试（`make check`，构建期在 build() 内执行）

清点口径 = `tests/Makefile.am` 的**两个 automake 注册面**（libyal 家族口径，
同 libvsgpt/0-20240504 先例）：

| 注册面 | 数量 | 实测 |
|---|---|---|
| `TESTS`（shell 入口脚本） | 5 | `PASS 4`（test_library.sh、test_glob.sh、test_write_functions.sh、test_tools.sh）＋ `SKIP 1`（test_smrawverify.sh） |
| `check_PROGRAMS`（C 测试程序） | 11 | 11/11 真实执行且通过（round-4 干净轮实测；runner 失败即中断语义 + create 日志 11 条编译行；逐项读数见 manifest tests 段与 reports/test-report.md） |
| **合计（N）** | **16** | 见 PR 正文与 reports/（按最终设备日志复算） |

- `check_PROGRAMS` 11 个：error、filename、glob、handle、information_file、
  io_handle、notify、support、tools_output、tools_signal、write。
- 驱动关系：test_library.sh 驱动 error/filename/information_file/io_handle/notify/
  support（LIBRARY_TESTS，无输入）+ handle（`LIBRARY_TESTS_WITH_INPUT`，input/
  缺失时按脚本内 `if test -d "input"` 分支退化为无输入运行——**不是跳过**）；
  test_glob.sh 自建 TMPDIR 输入驱动 smraw_test_glob；test_write_functions.sh 以
  `${TMPDIR}` 为输出目录驱动 smraw_test_write；test_tools.sh 驱动 tools_output/
  tools_signal。
- **唯一 SKIP**：`test_smrawverify.sh` 需要 `tests/input/` 夹具，发布用 orig
  tarball 不含该目录（`tar tzf … | grep -c '/input/'` = 0），脚本按上游规则
  `exit 77` → automake 记为 `SKIP`。
- `tests/Makefile.am` 的 `TESTS` 还含条件项 `test_python_module.sh`
  （`if HAVE_PYTHON_TESTS`）；本包 `--disable-python`，该条件不成立，未进入
  `TESTS`，**不计入 N**（不同口径不混用）。`check_SCRIPTS`（pysmraw_test_*.py、
  test_runner.sh 等）是测试支撑脚本，不是注册项，亦不混入。

## 消费者测试（`test_package/`，Conan L1）

- `test_libsmraw.c`（22 项断言）：版本串（`libsmraw_get_version()` = 上游
  20240506，非 Conan ref）、codepage 正常/错误路径、单段 RAW 打开/读回、
  seek 后读、offset 推进、handle 生命周期。
- `test_ohos.c`（23 项断言，仅 OHOS 编译运行）：`__OHOS__` 编译目标、TMPDIR 语义
  （存在/非只读 /tmp/可写）、在 TMPDIR 下合成 8 KiB **双段 Split RAW** 镜像
  （2×4 KiB segment 文件）并经 `libsmraw_handle_open(handle, filenames[], 2, …)`
  多文件名入口读回全链路——含**跨段边界 32 字节读**（offset 4088..4119）、
  段内 marker、media size、signal_abort、关闭释放。
- `smrawverify -V`：安装后的 CLI 产物加载共享库并输出版本（运行/加载验证）。
- 编译期已做 `clang -fsyntax-only -Wall -Wextra` 零告警自检（对源码树 include/）。

## 语言预检（R47）与工具侧误判（重要留痕）

`lang-preflight` 首跑判 `mixed → env_unsupported`（exit 2）：依据是根目录
`pyproject.toml`「python 打包 manifest」与源码统计冲突。人工复核证据：

1. 根目录 `pyproject.toml` 只有 3 行 `[build-system]`（setuptools/wheel），是
   **pysmraw python 绑定**的打包元数据；`setup.py` 头注释自述
   "Script to build and install Python-bindings."。libyal 把绑定打包元数据放在
   tarball 根，而非 `pysmraw/` 或 `lang/python/` 子目录——工具的绑定目录排除
   规则覆盖不到这个形态。
2. 主体语言纯 C：`c:216/222（97%）`，构建入口是 `configure`/`Makefile.am`
   （autotools），任务语言 cpp 兼容。
3. 副本排除绑定打包文件（pysmraw/、pyproject.toml、setup.py、setup.cfg*、
   smraw.net/）后重跑：`detected=cpp（autotools；c:209/212，99%）→ pass`。

结论：首跑为假阳性，不构成终止任务依据（辅助脚本/绑定打包元数据不决定主体
语言）；误判证据链完整保留于本节。该形态与 DRAFT-E586（libvsgpt 第 4 例）同族，
本次为第 5 次独立复现，已写 `feedback/pending/`。

## 已知限制

1. `smrawmount` 的 FUSE 挂载功能：OHOS/CI 无 libfuse，`AX_LIBFUSE_CHECK_ENABLE`
   探测为否，工具按上游默认条件编译（挂载路径在编译期降级）。`smrawmount -V`、
   `smrawverify -V` 不受影响。交付的 `commands.json` 声明两个 CLI。
2. Split RAW 的**写**路径与 `smrawverify` 端到端测试依赖 `tests/input/` 夹具，
   上游发布包不含，本包亦未自行构造端到端夹具（消费者测试已覆盖双段读回全链路；
   写路径由上游 `smraw_test_write` 单元测试以 TMPDIR 输出目录覆盖）。
3. 本版本 config.sub 对 `linux-ohos` 的拒绝未在本包单独复测（同 vintage 2023-06-23
   的 libvsgpt 设备实测拒绝），配方直接显式 GNU 三元组，conan create 干净轮全绿。
