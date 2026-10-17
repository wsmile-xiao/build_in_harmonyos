# libfshfs 20260130 适配笔记

## 当前状态

- 状态：`built`（真机 W3 构建 + 上游测试 + `test_package` 通过；制品未上传，故不标 `published`）
- 分支：`feat/libfshfs-20260130`；worktree：`/storage/Users/currentUser/ws/worktrees/libfshfs-20260130`
- 包目录：`archives/l/libfshfs/20260130`（全新包，`upstream/main` 此前无 `archives/l/libfshfs`）
- 构建系统：Autotools（发布包自带 `configure` / `aclocal.m4` / `config.guess` / `config.sub` / `Makefile.in`，**不需要** autoreconf）
- 编译器：`clang` / `clang++`（OHOS SDK，`/data/service/hnp/bin/clang`，15.0.4，Target `aarch64-unknown-linux-ohos`）
- 目标：`os=OHOS`、`arch=armv8`、`compiler=clang 15`、`build_type=Release`（`ci/conan/profiles/ohos-aarch64`）
- 环境变量：`CONFIG_SHELL=/data/service/hnp/bin/bash`、`SHELL=/data/service/hnp/bin/bash`
- 上游测试的 `HOME` 指向构建目录内的一次性目录（`build_folder/upstream-test-home`），不触碰操作者真实 `HOME`

## W0 依赖检查

上游 `configure.ac` 把 16 个同族 libyal 组件作为**本地**（bundled）组件参与构建：

`libbfio libcdata libcerror libcfile libclocale libcnotify libcpath libcsplit libcthreads libfcache libfdata libfdatetime libfguid libfmos libhmac libuna`

这些组件在发布包 tarball 内自带源码，**不注册为 Conan 依赖**（一库一分支，不把依赖适配混进本 PR）：

- `ohpcd` 远端与本地归档都没有对应 recipe，配方也不调用上游未锁定的 `synclibs.sh`；
- `build()` 开头做**闭包校验**：16 个组件目录与 5 个生成文件缺任一即报 `ConanInvalidConfiguration`，避免把"源码不完整"误诊成依赖缺失。

唯一的外部系统库是 **zlib**（HFS+ decmpfs/deflate 支持）：

- `configure.ac` 自动探测：`checking for zlib.h... yes` / `checking for zlibVersion in -lz... yes` → `DEFLATE compression support: zlib`；
- 头文件与库来自 OHOS SDK sysroot（`.../sysroot/usr/lib/aarch64-linux-ohos/libz.so`，`SONAME` 为无版本号的 `libz.so`），产物因此带 `DT_NEEDED libz.so`；
- 配方在 `package_info()` 用 `self.cpp_info.system_libs = ["z"]` 显式声明（`archives/l/**` 下 378 个已合入配方使用同一写法；libyal 同族此前的包不涉及 zlib，故 0 个先例），使静态消费者也能链接；
- 设备运行期实测可加载（见下"真机问题"第 5 条），不新增 Conan 依赖。

`libfuse` 只用于 `fshfsmount`，`configure` 以 `--with-libfuse=no` 关闭（OHOS 无 fuse 开发文件）；`pyfshfs` Python 绑定以 `--disable-python` 关闭。

## W1 源码与构建系统

- 上游项目：`https://github.com/libyal/libfshfs`
- 目标版本：`20260130`（`configure.ac` 的 `AC_INIT([libfshfs], [20260130], ...)`）
- 对应上游提交：`dd100d2ae96b12fe07d7082e94c5ed29319d280e`（author date `2026-01-30T18:28:06Z`）
- 上游测试入口：`make check`；`tests/Makefile.am` 注册 36 个 C 测试程序（`check_PROGRAMS`）

### 源码来源与身份核验

上游 GitHub release 资产已下线（实测 `https://github.com/libyal/libfshfs/releases/download/20260130/libfshfs-experimental-20260130.tar.gz`
返回 **HTTP 404**；releases API 当前只列出 `20260802`、`20260826`），因此使用 Debian 源包的 orig tarball 镜像：

- URL：`https://deb.debian.org/debian/pool/main/libf/libfshfs/libfshfs_20260130.orig.tar.gz`
- SHA256：`1d82c19fdbabd2442b37423e847e9a235e402436c1d2444b6920ab1f11912ef6`（1986111 字节）
- 交叉核验：Debian 源包清单 `libfshfs_20260130-1.dsc`（维护者 Debian Security Tools）里 `Checksums-Sha256`
  同一文件哈希与字节数一致，说明下载文件与 Debian 收录的 orig 完全一致；
- 上游身份核验：从 tarball 解出的 5 个关键文件（`configure.ac`、`Makefile.am`、`libfshfs/Makefile.am`、
  `include/libfshfs.h.in`、`tests/Makefile.am`）与上游提交 `dd100d2a` 的 raw 内容**逐字节一致**（`cmp` 全 SAME）；
- 未做整包与上游 tarball 的比对（上游资产不可得），已在 `manifest.yaml` 的 `release_artifact` 中如实说明。

### R47 语言预检的误判与人工复核（重要）

`lang-preflight` 对本包判 `detected_language=mixed → env_unsupported`，依据是
`lang_detect._manifest_scan()` 命中根目录 `pyproject.toml`（判 `build_system=setuptools`）。这是**误判**：

- 根目录 `pyproject.toml` 全文只有 `[build-system] requires = ["setuptools", "wheel"]`，属于**可选
  `pyfshfs` Python 绑定模块**的打包清单（`setup.py` 首行自述 "Script to build and install Python-bindings."），
  不代表包主体语言；
- 真正的构建系统是 Autotools：根目录 `configure.ac`（`AC_INIT([libfshfs],[20260130])`）+ `Makefile.am`（SUBDIRS，
  含 `pyfshfs`）+ 自带 `configure`；
- 源码统计：283 个 `.c` 为库主体（98%），3 个 `.cpp` 全部在 `ossfuzz/`（模糊测试骨架），3 个 `.py` 分别是
  `setup.py`（绑定构建脚本）与 `tests/pyfshfs_test_{support,volume}.py`（绑定测试辅助）——按 R47 边界规则
  "辅助脚本不决定主体语言"；
- 本配方 `--disable-python` 关闭绑定，`configure` 输出确认 `Python (pyfshfs) support: no`。

按 `notes/device-facts.md` §4.2 / §330「误判不构成终止任务的依据，按'辅助脚本不决定主体语言'人工复核留证"继续适配。
该误判类已有既有知识条目（见 `manifest.yaml` 的 `knowledge_ref`），本任务不再重复建草稿，只把设备实测证据落在本节与
`reports/` 里。编排侧以 `--skip-step lang-preflight` 记账（工具 rc=2 与原始输出已留档，重跑无意义），
`--start-note` 写明该步**已执行**而非未执行。

## W2/W3 配方与 test_package

`conanfile.py` 要点：

- `sources` 固定在 `conandata.yml`（URL + sha256），`source()` 显式传 `filename`，避免 Conan 对 Debian URL 的
  ZIP/tar 推断误判（`BadZipFile`）；
- `configure_args`：`--disable-python --with-libfuse=no --enable-static-executables=no`，OHOS 下追加
  `--build/--host=aarch64-unknown-linux-ohos`；`shared` 选项决定 `--enable-shared/--disable-static`（由
  `AutotoolsToolchain` 生成）；
- 构建并发显式限流：`make -j2`（设备 `os.cpu_count()=20` 而 affinity=8，conan 取前者会 2.5× 超订）；
- `package()`：`make install DESTDIR=<package_folder>` + 复制 `COPYING`、`COPYING.LESSER` 到 `licenses/`；
- `package_info()`：`libs=["fshfs"]`、`system_libs=["z"]`，并设置 `cmake_file_name`/`cmake_target_name`/`pkg_config_name`。

`test_package/` 为消费者视角测试，**直接调用被测包的公开 API 并断言版本/行为**（不是空壳）：

- 通用（`test_libfshfs.c`，14 断言）：版本串 `20260130`；`libfshfs_get_access_flags_read()`；`LIBFSHFS_OPEN_READ`
  一致性；`get_codepage` 默认 0；`set_codepage(1252)`/`(0)` 往返；`set_codepage(-1)` 错误路径；
  `check_volume_signature` 对普通文件返回 0、对 `H+` 与 `BD` 夹具返回 1、对缺失文件返回 -1 且带 error；
  `volume_initialize` → `volume_open`（非 HFS 文件失败且带 error）→ `volume_free` 生命周期。
- 鸿蒙专项（`test_ohos.c`，10 断言 + 2 个编译期守卫）：`__OHOS__` 与 `LIBFSHFS_VERSION` 编译期守卫；版本串；
  `/tmp` 只读时 `TMPDIR` 必须存在、非 `/tmp` 且可写（宿主可写时按 SKIP 上报，不计入通过）；临时文件 `mkstemp`/
  写读往返/清理；在设备 `TMPDIR` 下合成 1536 字节夹具（偏移 1024 处 `H+`）并用包内库做**正向**签名识别。

## 上游测试：清点、计数与证据

### 单位与数字

声明 N = **39**（上游 `tests/*.c` **源文件口径**，与外部审查实测口径一致）；其构成为 **36 个已执行程序 + 3 个辅助源文件**，逐项归因见下表。
另一单位另栏：注册程序口径 = `tests/Makefile.am` 的 `check_PROGRAMS`（上游当前 HEAD 同为 36）。

| 数字 | 含义 | 取数命令 |
| --- | --- | --- |
| **39** | **声明 N**：上游 `tests/*.c` 源文件总数（审方实测口径） | `ls tests/*.c \| wc -l` |
| **36** | 其中：`check_PROGRAMS` 注册测试程序（**已真实执行 36/36 PASS**） | `sed -n '/^check_PROGRAMS/,/^$/p' tests/Makefile.am \| sed '1s/check_PROGRAMS *=//' \| tr -d '\\' \| wc -w` |
| **3** | 其中：`_SOURCES` 辅助源文件（**不含独立用例**）：`fshfs_test_functions.c` / `fshfs_test_getopt.c` / `fshfs_test_memory.c` | `grep -n 'fshfs_test_\(functions\|getopt\|memory\)\.c' tests/Makefile.am`（如 :93/:125）；`awk '/^check_PROGRAMS/,/^$/' tests/Makefile.am \| grep fshfs_test_functions` → 无命中 |
| **36** | 上游当前 HEAD 注册数（注册口径下界核对） | 同上命令，对 `upstream/main` 的 `tests/Makefile.am` |
| **32** | `test_library.sh` 实际派发并通过的程序数 | `grep -c ' (PASS)' tests/test_library.sh.log` |
| **4** | 已注册但上游 runner 未派发、由配方补跑的 tools 程序数 | 见下"问题 4" |
| **3 / 1 / 2** | automake runner 汇总 TOTAL / PASS / SKIP | `grep -E '^# (TOTAL\|PASS\|SKIP\|FAIL\|ERROR)' tests/test-suite.log` |

程序级合计：**TOTAL 36 = PASS 36 + FAIL 0 + SKIP 0 + NOT_RUN 0**（注册程序口径；36 与上游 HEAD 下界差额为 0）；
声明 N（源文件口径）**39 = 36 + 3**，差额 3 为上述辅助源文件、无独立用例。
runner 级（单位是脚本，不是程序，**不并入 N**）：TOTAL 3 / PASS 1 / SKIP 2 / FAIL 0。

几个数字互不相同的原因见"问题 4"：`make check` 只执行 `TESTS` 里的 runner，而 runner 内部列表决定实际派发；
把 runner 汇总（3）或派发数（32）当成注册数都会少报，把 36 全写成 PASS 而没有补跑证据则是谎报；
而按源文件口径清点（39）时，必须把 3 个非程序辅助源文件逐项归因，不能算作已执行的用例。

### 逐项归因

| runner | 派发 | 结果 | 证据 |
| --- | --- | --- | --- |
| `tests/test_library.sh` | 30（`LIBRARY_TESTS`）+ 2（`LIBRARY_TESTS_WITH_INPUT`：`support` `volume`，无 `input/` 时按上游规则退化为无参数执行）= 32 | 32 PASS / 0 FAIL | `tests/test_library.sh.log` 32 个 ` (PASS)` 行、0 个 ` (FAIL)` 行 |
| `tests/test_tools.sh` | 0（`TOOLS_TESTS="";` 且 `TOOLS_TESTS_WITH_INPUT="";`） | SKIP(77) | `tests/test_tools.sh.log`：`SKIP test_tools.sh (exit status: 77)` |
| `tests/test_fshfsinfo.sh` | 0（输入驱动，发布包不含 `tests/input`） | SKIP(77) | `tests/test_fshfsinfo.sh.log`：`Test input directory not found.` |
| `tests/test_python_module.sh` | 不参与（`--disable-python` → `HAVE_PYTHON` 为假） | 未运行 | `tests/Makefile.am` 的 `TESTS_PYFSHFS` 条件块；`configure` 输出 `Python (pyfshfs) support: no` |
| 4 个 `fshfs_test_tools_*`（`check_PROGRAMS` 内） | 配方补跑 | 4 PASS | `tools_info_handle` / `tools_mount_path_string` / `tools_output` / `tools_signal` 各 `(PASS)` |

`test_fshfsinfo.sh` 与 `test_tools.sh` 的 SKIP 都是**上游规则**（`exit 77`），不是构建失败：前者缺 `input/` 夹具
（发布 tarball 不含），后者上游在该版本把两个派发列表留空；两者都不影响 36 个注册程序的可执行性。

## 真机问题与处理

1. **HMDFS 上 Autoconf 的 `umask 077` 临时目录不可用** → `configure` 里有 2 处 `umask 077`（autoconf 的
   `conf$$-$RANDOM` 目录），HMDFS 下创建出的 0700 目录会导致后续写入 `Permission denied`。构建期把这 2 处
   替换为 `umask 022` 并全程 `umask 022`（同族 libvhdi/libfsntfs 的既有处置）。
2. **HMDFS 禁止直接执行源码树脚本** → 用 `CONFIG_SHELL=/data/service/hnp/bin/bash` 显式解释 `configure`；
   `make check` 传 `LOG_COMPILER="$CONFIG_SHELL"`。
3. **libtool 包装脚本 vs `.libs` 真 ELF** → 上游 `tests/test_runner.sh` 的普通分支直接执行 `./fshfs_test_*`
   （libtool 包装 shell 脚本）。构建期为该文件的两处执行分支插入上游自带的 `find_binary_executable` 解析
   （`<dir>/.libs/<name>`），并给 `make check` 注入 `LD_LIBRARY_PATH=<src>/libfshfs/.libs`。只改"怎么启动测试"，
   **不改任何上游用例的源码、断言或语义**。
4. **已注册但未被派发的 4 个 tools 程序** → 上游 `tests/test_tools.sh` 两个列表为空（见上）。配方在
   `make check` 之后用**同一个上游 harness**（`. ./test_runner.sh` + `run_test_with_arguments`）补跑这 4 个程序，
   使程序级合计覆盖全部 36 个注册项；若上游将来填上列表，配方里的判据会自动跳过补跑（避免重复计数）。
5. **系统 zlib 依赖** → 产物 `libfshfs.so` 带 `DT_NEEDED libz.so`（见 W0）。设备实测可加载：用
   `ctypes.CDLL` 加载包内 `libfshfs.so` 成功，`fshfs_test_deflate` 直接运行 rc=0（不依赖 `LD_LIBRARY_PATH` 里的
   LLVM 目录）。配方以 `cpp_info.system_libs=["z"]` 显式声明。
6. **门禁读数差异（非阻塞，原始读数留档）** → `conan_verify` 的 L4 对 `bin/` 两个工具打印 `NX=disabled` 安全警告；
   原始 `readelf -lW` 读数为 `GNU_STACK … RW`（无 E 位，NX 生效），`readelf -dW` 显示 `BIND_NOW`、
   `FLAGS_1: NOW PIE`、`GNU_RELRO` 存在；交付的共享库 `libfshfs.so.1.0.0` 同样满足（`SONAME libfshfs.so.1`、
   `BIND_NOW`、`GNU_RELRO`、`GNU_STACK RW`）。这是工具判定与工具链产物的形态差异，**不涉及交付的 .so**。
   W3 本地 CI 的 `L2_RESULT=skip` 同理是探针形态差异：libyal 工具用短选项，`fshfsinfo -V` 正常输出
   `fshfsinfo 20260130`，而 W3 探针用 `--version/--help`（工具报 `unrecognized option: -`）；`conan_verify` 的 L2
   用 `-V` 因此 PASS。两处均按非阻塞如实登记，未改写为 PASS。

## 技术债与合规说明

- 本节问题 1、3、4 属于**构建期对上游源码/生成文件的就地修改**（`configure` 是 autoconf 生成文件）。按 R6
  "探索阶段改源码 + 记 notes"的口径处理，**不引入 `patches/` 静态补丁**，理由是：这些修改只在 `settings.os=OHOS`
  时生效，静态补丁会无条件改到 Linux 构建；且均已用"needle 计数 + 数量不符即 `ConanInvalidConfiguration`"做
  失效保护（`test_runner.sh` 两处 needle 各需出现 2 次，实测 2/2）。
- 期望的上游修复方式（P006 技术债登记）：①autoconf 允许通过环境变量覆盖临时目录 umask；②`test_tools.sh` 的
  `TOOLS_TESTS` 列表补全注册程序；③`test_runner.sh` 普通分支默认解析 `.libs`（这三条对所有在 HMDFS/受限环境下
  跑 libyal 测试的适配都成立）。
- 未修改任何上游测试用例的源码或断言；未新增/删除/跳过上游用例；`test_package` 用例与上游用例**分栏统计**。
- 提交面不含任何 `*.log`/二进制；真机日志以逐字 `.md` 摘要落 `reports/`（该目录被 `.gitignore` 覆盖，不进 PR）。

## 知识增量评估（路径 B）

可复用增量：**Autotools 包的 `make check` 只计入 `TESTS` runner，而 N 的清点单位是 `check_PROGRAMS` 注册数**；
上游 runner 内部列表为空时，已构建已注册的程序不会被派发（automake 只记 runner SKIP），同一份构建里出现
`3 / 32 / 36` 三个都"正确"却互不相同的数字。条目给出清点命令、逐程序证据的正确取数位置
（`tests/<runner>.log`，不是 `test-suite.log`、也不是 make 的 stdout）、用上游 harness 补跑的口径与分栏申报方式。

- 草稿：`knowledge/drafts/E589-draft-libfshfs-check-programs-runner-dispatch.kv` / `.md`
- 编号：`E589`（编排方按 **git 树口径**（`git ls-tree -r upstream/main -- knowledge/` 提取 E 号 + 各 worktree 新增项）复核为空号后保留）。
  工具取号不可作唯一判据：`tools/knowledge_id.py --claim` 对同一任务给出 `E565`，而 `E565` 在 `upstream/main` 树内已被 16 个文件占用
  （主线面扫描落后于主线，实测同类假空号在本批 libfsxfs / libfvde 上各命中一次）；本任务的编号以 git 树复核结果为准。
- 去重边界：`DRAFT-10251-libnfc-tools-1.8.0-autotools-test-framework-guard`（configure 守卫把测试目标整体排除，
  "根本没构建"）与 `DRAFT-no-upstream-tests-drive-real-interface`（上游确无测试套件）都不覆盖"已构建已注册但未派发"；
  `DRAFT-libfsntfs-release-archive-closure` 覆盖发布包闭包与镜像回退，本条不重复主张闭包审计。
- 其余增量（HMDFS umask、`CONFIG_SHELL`/`LOG_COMPILER`、libtool `.libs`、发布包闭包、镜像回退、语言误判）
  均已被既有条目覆盖，按 `manifest.yaml` 的 `knowledge_ref` 行尾引用，不重复建草稿。
