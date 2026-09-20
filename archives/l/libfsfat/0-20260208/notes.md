# libfsfat 0-20260208 适配笔记

## 状态

- 状态：built（真机 W3 `conan create` + 上游 `make check` + `test_package` 均真实执行）
- 分支：`feat/libfsfat-0-20260208`；包目录：`archives/l/libfsfat/0-20260208/`
- 构建系统：autotools（上游自带生成的 `configure`，无需自举；设备与 CI worker 都不需要 automake/autoconf）
- 编译器：clang 15.0.4（OHOS SDK，`/data/service/hnp/bin/clang`），目标 aarch64-unknown-linux-ohos
- 交付物：共享库 `libfsfat.so.1.0.0`（+ `libfsfat.so.1`、`libfsfat.so`）、`include/libfsfat.h` 与
  `include/libfsfat/*.h`、`bin/fsfatinfo`、`bin/fsfatmount`、`lib/pkgconfig/libfsfat.pc`、`licenses/COPYING*`

## 源码溯源（版本号为何是 `0-20260208`）

- 上游项目：`https://github.com/libyal/libfsfat`；本包版本 `0-20260208` 对应上游 2026-02-08 快照。
- **上游未发布该版本的 release 资产**：
  `https://github.com/libyal/libfsfat/releases/download/20260208/libfsfat-alpha-20260208.tar.gz`
  与 `.../libfsfat-experimental-20260208.tar.gz`、`.../releases/tag/20260208` 实测均 **404**。
- 因此使用权威发行版归档（Debian pool）的 pristine orig tarball，并用 Debian 源包
  **PGP 签名 .dsc** 的 `Checksums-Sha256` 锚定内容：

```sh
$ curl -sS -o libfsfat_0~20260208.orig.tar.gz \
    "https://deb.debian.org/debian/pool/main/libf/libfsfat/libfsfat_0~20260208.orig.tar.gz"
$ sha256sum libfsfat_0~20260208.orig.tar.gz
043cf14a9067b42fdef9b914cc0e00ed3354d82c9a94ed956390fd1a1b8599fb   # 1633953 字节
$ curl -sS "https://deb.debian.org/debian/pool/main/libf/libfsfat/libfsfat_0~20260208-1.dsc" | grep -A2 Checksums-Sha256
 043cf14a9067b42fdef9b914cc0e00ed3354d82c9a94ed956390fd1a1b8599fb 1633953 libfsfat_0~20260208.orig.tar.gz
```

  `.dsc` 声明的 `Version: 0~20260208-1`（Debian 用 `~` 表示该上游无正式版本号），
  Conan 版本号按本仓库既有的 `0-<日期>` 口径写作 `0-20260208`（同族先例
  `archives/l/lib1305/0-20250415`、`archives/l/lib25519/0-20260614`）。
- tarball 顶层目录为 `libfsfat-20260208/`（`strip_root=True` 直接命中），内部自带
  `configure`、`aclocal.m4`、`config.guess`（timestamp 2024-07-27）、`config.sub`、
  `Makefile.in` 等生成文件，以及 15 个 standalone libyal 组件目录
  （libbfio libcdata libcerror libcfile libclocale libcnotify libcpath libcsplit
  libcthreads libfcache libfdata libfdatetime libfguid libhmac libuna）。

## W0 依赖发布检查：无外部依赖（none）

三条独立证据（详见任务侧 `w0-deps.txt`）：

1. `configure.ac` 全文无 `PKG_CHECK_MODULES`、无 `AC_CHECK_LIB`；只有
   `AC_CHECK_HEADERS([stdarg.h varargs.h])`（系统头）。
2. 15 个 libyal 组件以 standalone 形式内嵌在发布包内（`AX_LIB*_CHECK_ENABLE` 宏），
   `Makefile.am` 的 `SUBDIRS` 逐个树内构建。
3. Debian 源包 `Build-Depends: dpkg-dev, debhelper-compat, dh-python, pkgconf,
   python3-dev, python3-setuptools` —— 无任何 libyal 二进制开发包依赖。

libfuse 只服务可选的 `fsfatmount`，配方显式 `--with-libfuse=no`；python 绑定
（`pyfsfat`）显式 `--disable-python`。

## 构建步骤（配方实际序列）

```sh
# build() 内（OHOS）：CONFIG_SHELL=/data/service/hnp/bin/bash
# 1) configure 内 2 处 `umask 077` → `022`（HMDFS，见平台适配表）
"$CONFIG_SHELL" ./configure \
    --prefix=<pkg> --bindir=<pkg>/bin --libdir=<pkg>/lib --includedir=<pkg>/include \
    --enable-shared --disable-static --disable-python --with-libfuse=no \
    --enable-static-executables=no \
    --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos
make -j<n>
make -j<n> check LOG_COMPILER=/data/service/hnp/bin/bash   # 上游测试，见下
make install DESTDIR=<pkg>                                  # Autotools.install()
```

设备原生（不经 Conan）复核同一序列：`configure` / `make -j2` / `make -j2 check` /
`make install` 全部 rc=0（日志 `native-build.out`、`native/configure.log`、
`native/make.log`、`native/make-check.log`）。

## 平台适配（全部内联在 `conanfile.py build()`，无 `patches/` 文件）

| # | 现象 | 根因 | 处置 |
|---|------|------|------|
| 1 | HMDFS 上 configure 报临时目录不可写 | `configure` 内 2 处 `umask 077` 建出的 `confXXXX` 目录在 HMDFS 上连创建者都无法写入（E011 同族实测） | 只把源码树 `configure` 的 2 处 `umask 077` 改为 `022`，并让整个构建过程保持 `umask 022`；`config.status` 由改写后的 configure 生成，实测无需二次替换 |
| 2 | `./configure` 报 `cannot guess build type` | 随包 `config.guess`（2024-07-27）不识别 HarmonyOS（`uname -s` = `HarmonyOS`） | OHOS 下显式传 `--build/--host=aarch64-unknown-linux-ohos`；随包 `config.sub` **原生接受** `linux-ohos`（实测 `config.sub aarch64-unknown-linux-ohos` → `aarch64-unknown-linux-ohos`），故**不需要**改 `config.guess`/`config.sub`；libtool 走共享库 PIC 分支，产出 `libfsfat.so.1.0.0` |
| 3 | HMDFS 上直接执行源码树脚本受限 | 设备对脚本执行/临时目录语义受限 | OHOS 下用 profile `[buildenv]` 注入的 `CONFIG_SHELL=/data/service/hnp/bin/bash` 显式启动 `configure`；`make check` 的 `TESTS` 入口同为 bash 脚本，用 automake 的 `LOG_COMPILER` 指定同一解释器 |
| 4 | 测试程序需要读回构建树内的共享库 | `make check` 在树内运行未安装的库 | 仅在本进程子树内把 `libfsfat/.libs` 前置进 `LD_LIBRARY_PATH`，退出时还原原值 |

**R6 声明（如实登记，唯一例外）**：本包**不修改**上游任何 C/H 源文件、测试脚本、`Makefile.am`，
也不新增 `patches/` 补丁文件；唯一的**生成脚本**改动是上表第 1 行的 `configure` 内 2 处
`umask 077`→`022`（在 Conan 缓存内的源码副本上执行，不改动仓库内任何文件）。这是 E011 的既有
处置口径，同族先例采用同一做法（`archives/l/libesedb/20240420` 的 `patches/0004-configure.patch`、
libfsntfs 20251028 的 `build()`）；不改时 HMDFS 上 `configure` 必然以
`cannot create …/subs1.awk: Permission denied` 失败（E011 实测形态）。

**关于上游 `tests/test_runner.sh`（不需要改写，与同族先例不同）**：该文件用
`file -b` 输出里是否含字面量 `POSIX shell script` 判断「测试程序是不是 libtool 包装脚本」，
而 OHOS 的 `file` 输出形如 `/bin/sh script`（设备实测），判定因此不成立、测试直接执行
libtool 包装脚本本身。设备原生实测 `make check` 全绿（19 个 C 测试程序全部 PASS），
故**没有**像同族先例那样在 `build()` 内改写 `test_runner.sh`。

## 上游测试（`make check`，构建期在 build() 内执行）

清点口径 = `tests/Makefile.am` 的**两个 automake 注册面**（与上游当前 HEAD 逐项一致，
实测 diff 为空）：

| 注册面 | 数量 | 本包实测 |
|---|---|---|
| `TESTS`（shell 入口脚本） | 3 | `PASS 2`（test_library.sh、test_tools.sh）＋ `SKIP 1`（test_fsfatinfo.sh） |
| `check_PROGRAMS`（C 测试程序） | 19 | 全部真实执行、`PASS 19` |
| **合计（N）** | **22** | `PASS 21` / `SKIP 1` / `FAIL 0` |

- `check_PROGRAMS` 19 个：allocation_table、block_descriptor、block_tree、block_tree_node、
  boot_record、directory、directory_entry、error、extent、file_entry、io_handle、name、
  notify、support、volume、tools_info_handle、tools_mount_path_string、tools_output、tools_signal。
- 其中 15 个由 `test_library.sh` 驱动（`LIBRARY_TESTS` 13 个 + `LIBRARY_TESTS_WITH_INPUT`
  的 support、volume），4 个由 `test_tools.sh` 驱动。
- **`support`/`volume` 不是跳过**：`test_library.sh` 在 `tests/input/` 缺失时按上游逻辑
  退化为无输入运行（脚本内的 `if test -d "input"` 分支），设备实测两者都真实执行并 PASS。
- **上游当前 HEAD 的测试布局已变（已逐项核对）**：上游 HEAD 的 `tests/Makefile.am` 改成
  Autotest 套件（`check_AUTOTESTS = test_library test_manpages test_tools`，由 `check-local`
  驱动），而本包 2026-02-08 版本仍是 shell-runner 布局（`TESTS` + `check_PROGRAMS`）。
  两个布局的 `check_PROGRAMS` 均为同一 19 个程序（设备实测 `diff` 为空），故声明
  N=22 不低于审方按上游 HEAD 独立清点的下界；`AT_SETUP` 用例数是另一计量单位，未混入。
- **唯一 SKIP**：`test_fsfatinfo.sh` 需要 `tests/input/` 夹具，而发布用 orig tarball
  不含该目录（`tar tzf ... | grep -c '/input/'` = 0），脚本按上游规则 `exit 77` →
  automake 记为 `SKIP`。原始读数（设备原生轮，`tests/test-suite.log` 逐字）：

```text
=============================================
   libfsfat 20260208: tests/test-suite.log
=============================================

# TOTAL: 3
# PASS:  2
# SKIP:  1
# XFAIL: 0
# FAIL:  0
# XPASS: 0
# ERROR: 0

SKIP: test_fsfatinfo.sh
=======================

Test input directory not found.
SKIP test_fsfatinfo.sh (exit status: 77)
```

```text
# tests/test_library.sh.log
Testing: allocation_table (PASS)
Testing: block_descriptor (PASS)
Testing: block_tree (PASS)
Testing: block_tree_node (PASS)
Testing: boot_record (PASS)
Testing: directory (PASS)
Testing: directory_entry (PASS)
Testing: error (PASS)
Testing: extent (PASS)
Testing: file_entry (PASS)
Testing: io_handle (PASS)
Testing: name (PASS)
Testing: notify (PASS)
Testing: support (PASS)
Testing: volume (PASS)
PASS test_library.sh (exit status: 0)
```

```text
# tests/test_tools.sh.log
Testing: info_handle (PASS)
Testing: mount_path_string (PASS)
Testing: output (PASS)
Testing: signal (PASS)
PASS test_tools.sh (exit status: 0)
```

## 消费者测试（`test_package/`，Conan L1）

| 文件 | 平台 | 断言数 | 内容 |
|---|---|---|---|
| `test_libfsfat.c` | 全部 | 11 | 版本串、读访问标志、codepage 正常/错误路径、`set_codepage`、`check_volume_signature` 的 NULL 与不存在文件错误路径、volume 初始化/打开错误路径/释放 |
| `test_ohos.c` | OHOS | 20 | `__OHOS__` 编译目标、TMPDIR 语义（存在、非 `/tmp`、可写）、**合成 FAT-16 镜像读回链路**：写盘生成合法 FAT-16（卷标项 + HELLO.TXT）、卷签名、打开、文件系统格式枚举、卷标、根目录项数、按 UTF-8 路径取文件项、文件大小、读回内容、关闭释放、镜像清理 |

`test_ohos.c` 的镜像由测试自身用纯 POSIX 写盘生成（4 MiB、8095 个数据簇 → FAT-16），
不依赖任何外部夹具，因此这条链路在 CI 与设备上都能真实执行。另外 `test()` 内还执行
安装后的 `bin/fsfatinfo -V`，验证 CLI 产物能加载共享库（运行/加载验证）。

**三处公开 API 的反直觉约定**（消费者测试按实测值断言，避免"想当然"的假绿）：

1. `libfsfat_volume_get_file_system_format()` 写回的是**单字节枚举**
   `LIBFSFAT_FILE_SYSTEM_FORMAT_*`（`FAT16 = 3`），不是字符串；
2. `libfsfat_volume_close()` **成功返回 0**（头文件注明 "Returns 0 if successful or -1 on error"）；
3. `libfsfat_get_version()` 返回**上游版本串 `20260208`**，不是本包的 Conan 版本 `0-20260208`。

## 设备原生验证（不经 Conan 的独立复核）

```sh
$ sh "$TASK_DIR/native-build.sh"
=== [1/5] umask 077 -> 022 in configure (E011) ===      # 2 -> 0 处
=== [2/5] configure (autotools, OHOS clang 15.0.4) ===  # configure rc=0
=== [3/5] make -j2 ===                                  # make rc=0
=== [4/5] make -j2 check (sandbox HOME=...) ===          # make check rc=0
=== [5/5] make install (DESTDIR staging) ===             # install rc=0
```

```sh
# 消费者测试对「已安装」产物（DESTDIR staging prefix）编译并运行
$ clang test_libfsfat.c -o test_libfsfat -I<prefix>/include -L<prefix>/lib -lfsfat
$ clang test_ohos.c     -o test_ohos     -I<prefix>/include -L<prefix>/lib -lfsfat
$ LD_LIBRARY_PATH=<prefix>/lib ./test_libfsfat
libfsfat 0-20260208 consumer test: 11 assertions passed
$ LD_LIBRARY_PATH=<prefix>/lib TMPDIR=<writable> ./test_ohos
libfsfat OHOS-specific test: 20 assertions passed (FAT-16 image round trip under TMPDIR)
$ LD_LIBRARY_PATH=<prefix>/lib <prefix>/bin/fsfatinfo -V
fsfatinfo 20260208
```

## W3 本地 CI 模拟（`finish` Step 5，`ci/conan/build_and_test.sh`）

逐字读数（`reports/w3-local-ci.log`）：

```text
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=skip: fsfatinfo version/help failed, fsfatmount failed
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
```

```text
  Total:   1
  Success: 1
  Failed:  0
```

- `L1e` 破坏性反向验证通过：`[ok] L1e: Negative test confirmed — test genuinely depends on libfsfat`
  （移走 `bin/`、`lib/`、`include/` 后消费者测试确实失败）。
- **L2 为非阻塞 skip，两个独立成因都已实测定位**（两个工具都命中）：
  ① **探针选项约定不匹配（主因）**：CI 的 L2 探针用长选项 `--version` / `--help`
     （`ci/conan/build_and_test.sh` 的 L2 段），而 libyal 工具只接受短选项。设备实测
     （缓存内安装产物，注入运行环境）：
     `fsfatinfo -V` rc=0、`-h` rc=0、`--version` rc=1、`--help` rc=1（`fsfatmount` 同）；
     长选项下工具先打印版本横幅再报 `unrecognized option: -`。**因此注入运行环境不会让 L2 变 pass**。
     ①的处置建议已写 `feedback/pending/2026-09-19-libfsfat-0-20260208.md`。
  ② **探针不注入运行环境**：`bin/fsfatinfo`、`bin/fsfatmount` 的 `RUNPATH` 是 libtool 按
     `--prefix` 写下的 `//lib`，而包内共享库在 `<pkg>/lib`；不设 `LD_LIBRARY_PATH` 时加载器报
     `Error loading shared library libfsfat.so.1 (needed by …/bin/fsfatinfo)`（rc=127）。
     注入后短选项正常（`LD_LIBRARY_PATH=<pkg>/lib fsfatinfo -V` → `fsfatinfo 20260208`，rc=0），
     `test_package` 的 `test()` 就是按该方式验证的。
  同族先例（libfsntfs 20251028）的 L2 同样是 "non-blocking skip"。

## 已知工具侧偏差（如实登记，非本包失败）

`finish` Step 3 的 `clean-verify`（G0 干净构建）报 `configure 失败 (exit 1)`，根因在工具侧，
不在本包：

1. 实际运行的是 **overlay 副本** `framework/overlay/scripts/ohc/clean_verify.py`
   （`finish` 在本任务目录打印了 `[framework-overlay] 生效：… clean_verify …` 横幅）：
   它用 `re.search(r'configure_options:\s*["\']?(.*?)["\']?\n', …)` 取配置项后交给
   `_shell_ready_configure_options()`，该函数只覆盖空值形态、flow 列表与多段标量，
   **不支持 YAML 块列表**——本 manifest 的块列表被取成 `- "--enable-shared"`，按空白切分后
   向 configure 传入一个裸 `-`，于是 `configure: error: unrecognized option: '-'`。
   同目录日志里还有 `shell-init: error retrieving current directory: getcwd: …` 的 hnp bash 形态
   （E386 已知现象）。
1b.（仓库版另一形态，供工具侧一并修）`scripts/ohc/clean_verify.py` 的同一正则对块列表
   **只取到首项并静默丢弃其余 6 项**（设备实测：仓库版解析结果为 `--enable-shared` 单选项）。
   两者根因相同（正则不识别块列表），失败形态不同，修法均为"块列表按 YAML 解析"。
2. 该步骤**不施加配方内联的 OHOS 适配**（`umask 077`→`022`、显式 `--build/--host` 三元组），
   因此对"适配写在 `build()` 内、无 `patches/` 文件"的包必然失败。

后果与处置：`finish` 把它记为**告警**并继续（Step 4/5 的 `conan-verify` 与 W3 真实构建门禁
全部 PASS，`EXIT_REASON: finish_success`、rc=0，`.ci-result.json` 由 W3 写入 exit_code=0）。
本报告不把它写成"通过"；工具侧修法建议已写
`feedback/pending/2026-09-19-libfsfat-0-20260208.md`。

## 语言预检（R47）与工具侧误判

`lang-preflight` 对本包判 `detected_language=mixed` → 终态 `env_unsupported`，**判据不成立**：
包主体是 C（232 个 `.c` 占 98%，autotools `configure` 为真实构建入口），命中
`manifest=python` 的 `pyproject.toml`/`setup.py`/`setup.cfg` 是**可选 Python 绑定模块
（`pyfsfat`）的打包元数据**（`setup.cfg` 自述 `description = Python bindings module for
libfsfat`，`pyproject.toml` 全文只有 3 行 setuptools 后端声明），且配方已
`--disable-python`。逐字原始输出与复核见任务侧 `lang-preflight-review.md`；
该步在编排中按 `--skip-step` 记为**未执行**（不是通过）。

## 已知限制

1. `test_fsfatinfo.sh`（1/22）在上游发布包缺少 `tests/input/` 夹具时按上游规则 SKIP，
   非失败；FAT 读取路径由 `test_ohos.c` 的合成 FAT-16 镜像读回链路替代覆盖。
2. `tests/test_fsfatinfo.sh`、`test_manpage.sh`、`test_python_module.sh` 依赖
   `input/` 夹具或 python 绑定，未纳入本次运行；`test_python_module.sh` 只在
   `--enable-python` 时进入 `TESTS`（本包显式关闭）。
3. `fsfatmount` 在 `--with-libfuse=no` 下按上游降级分支构建（可执行但不提供挂载），
   只做 `-V` 加载验证。
