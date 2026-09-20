# libfsxfs 20240501 适配笔记

## 编译环境

- 构建系统：autotools（发布包自带生成好的 `configure` / `aclocal.m4` / `config.guess` / `config.sub` / `Makefile.in`）
- 编译日期：2026-09-19
- 编译器：`clang` / `clang++` 15.0.4（OHOS SDK，`/data/service/hnp/bin/clang`），profile `ci/conan/profiles/ohos-aarch64`（`os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.version=15 build_type=Release`）
- 解释器：`CONFIG_SHELL=/data/service/hnp/bin/bash`（设备无 `/bin/bash`，`/bin/sh` 是 toybox）
- 并发：`-c tools.build:jobs=2`（设备 `os.cpu_count()`=20 而 affinity=8，见配方 `build()` 里的 `jobs = min(conf, 4)`）
- 状态：built

## 源码溯源

上游 GitHub 仓库已重置，**20240501 的 tag 与 release 资产都不存在**：

```text
$ git ls-remote --tags https://github.com/libyal/libfsxfs
1d4b4b2e80fc79042b96f6fdc5e66f060c6b9ec9	refs/tags/20260703
3ab64d277f19dd1d8235ee46a90f5d78374461d5	refs/tags/20260901

$ curl -sS -o /dev/null -w '%{http_code}' -L \
    https://github.com/libyal/libfsxfs/releases/download/20240501/libfsxfs-experimental-20240501.tar.gz
404
$ curl -sS -o /dev/null -w '%{http_code}' -L \
    https://github.com/libyal/libfsxfs/archive/refs/tags/20240501.tar.gz
404
```

因此固定源改用 **Debian 的 pristine orig tarball**（无 `+dfsg`、无重打包），
内容哈希由 **PGP 签名的** `libfsxfs_20240501-1.dsc` 锚定：

```text
Checksums-Sha256:
 b2abc65377fcffefdcf2d426b86b5fc06322380b3766d61b7074048fa1cf4717 1714269 libfsxfs_20240501.orig.tar.gz

$ sha256sum libfsxfs_20240501.orig.tar.gz
b2abc65377fcffefdcf2d426b86b5fc06322380b3766d61b7074048fa1cf4717  libfsxfs_20240501.orig.tar.gz
$ head -c 2 libfsxfs_20240501.orig.tar.gz | od -An -tx1
 1f 8b
$ gzip -t libfsxfs_20240501.orig.tar.gz && echo ok
ok
```

展开后是**自包含闭包**（923 个条目）：15 个 bundled libyal 组件
（`libbfio libcdata libcerror libcfile libclocale libcnotify libcpath libcsplit
libcthreads libfcache libfdata libfdatetime libfguid libhmac libuna`）
与生成好的 Autotools 文件全部在包内。配方 `build()` 早期校验该闭包，缺失即报
`ConanInvalidConfiguration` 并拒绝走 `synclibs.sh`。

> PF7 源 URL 闸把 `deb.debian.org` 归为「Debian 下游重打包源」并告警。本条属**确定性误报**：
> 该 URL 指向的就是 libyal 自己的发布包（不是 Debian 二次打包），且上游资产已 404，
> Debian 镜像是唯一可得的权威副本，其哈希由 PGP 签名 `.dsc` 锚定。
> 因此建 PR 时按 `--no-preflight` 跳过并在 PR 正文「补充说明」留痕。

## 三元组选型（本轮唯一一次 G2 失败）

第一版配方照抄同族先例 `libvhdi/20251119`，用 `--build/--host=aarch64-unknown-linux-ohos`，
在 configure 第一阶段硬失败（逐字，`reports/conan-create.log`）：

```text
checking build system type... Invalid configuration 'aarch64-unknown-linux-ohos': OS 'ohos' not recognized
configure: error: /data/service/hnp/bin/bash ./config.sub aarch64-unknown-linux-ohos failed
```

现场取证（**不要按族照抄**——同族版本之间结论相反）：

```text
$ grep -c ohos config.sub
0
$ ./config.sub aarch64-unknown-linux-ohos ; echo rc=$?
Invalid configuration 'aarch64-unknown-linux-ohos': OS 'ohos' not recognized
rc=1
$ ./config.sub aarch64-unknown-linux-gnu ; echo rc=$?
aarch64-unknown-linux-gnu
rc=0
```

改用 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`（**两者必须相同**）：

```text
checking build system type... aarch64-unknown-linux-gnu
checking host system type... aarch64-unknown-linux-gnu
checking whether we are cross compiling... no
...
config.status: creating common/config.h     # 新生成的那份含 108 个 #define HAVE_*
```

> 读数口径：`grep -c 'define HAVE_' <build_folder>/common/config.h` = **108**（configure 新生成）。
> 上游 tarball 内**自带**的 `common/config.h` 是发布包遗留的旧文件、含 119 个，会被 `config.status`
> 覆盖——不要拿 tarball 里那一份当读数（本笔记早期版本误引过该数字，W4 审计 P2-R51 已纠正）。

E007 警告「用 `--build/--host` 绕过会误判为交叉编译、AC_RUN_IFELSE 全部跳过」——
实测该后果只在 **build ≠ host**（真交叉）时成立；取同一个 GNU 三元组时 build == host，
configure 明确打印 `cross compiling... no`，run test 正常执行。该反证已写进
`knowledge/drafts/DRAFT-E587-libyal-ohos-triplet-variance.{kv,md}`。

复现脚本：`$HOME/tmp/libfsxfs-20240501/repro-e587-config-sub-triplet.sh`。

## 编译步骤

```sh
# 1) 取源 + 校验（见「源码溯源」）
curl -sSL -o libfsxfs_20240501.orig.tar.gz \
  https://deb.debian.org/debian/pool/main/libf/libfsxfs/libfsxfs_20240501.orig.tar.gz

# 2) 采信轮（清缓存 → 8 道门禁 → 证据副本 → finish 前快照）
sh "$HOME/ws/tools/conan_verify_round.sh" libfsxfs 20240501 \
   --repo "$TARGET_REPO" --task-dir "$TASK_DIR"

# 3) 收尾与复核
ohc-run.py finish libfsxfs 20240501 built
sh "$HOME/ws/tools/finish_restore.sh" --apply
python3 "$HOME/ws/tools/capture_evidence.py" --verify "$TASK_DIR/evidence-index.json"
```

配方内实际执行的 configure（逐字，`manual-create-1.log:103`）：

```text
RUN: "/data/service/hnp/bin/bash" ".../configure" --enable-shared --disable-static --prefix=/ \
  '--bindir=${prefix}/bin' '--sbindir=${prefix}/bin' '--libdir=${prefix}/lib' \
  '--includedir=${prefix}/include' '--oldincludedir=${prefix}/include' \
  --disable-python --with-libfuse=no --enable-static-executables=no \
  --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu
```

## 上游测试证据（逐字）

`make check` 的 automake 汇总（`tests/test-suite.log`，本任务留存
`$HOME/tmp/libfsxfs-20240501/evidence-manual/test-suite.log`，sha256
`04b4a336c26ccdf69cf2e5a7bf473ed63cefec452d7662f320119035a484eede`）：

```text
=============================================
   libfsxfs 20240501: tests/test-suite.log
=============================================

# TOTAL: 3
# PASS:  2
# SKIP:  1
# XFAIL: 0
# FAIL:  0
# XPASS: 0
# ERROR: 0

.. contents:: :depth: 2

SKIP: test_fsxfsinfo.sh
=======================

Test input directory not found.
SKIP test_fsxfsinfo.sh (exit status: 77)
```

`tests/test_library.sh.log`（22 个程序全部真实执行并通过；sha256
`434fd728761131625fbf49af0db290250d90b438ef2bc4abc2756114e394546f`）：

```text
Testing: attribute_values (PASS)
Testing: attributes_leaf_block_header (PASS)
Testing: attributes_table (PASS)
Testing: attributes_table_header (PASS)
Testing: block_directory_footer (PASS)
Testing: block_directory_header (PASS)
Testing: btree_block (PASS)
Testing: btree_header (PASS)
Testing: buffer_data_handle (PASS)
Testing: directory_entry (PASS)
Testing: directory_table_header (PASS)
Testing: error (PASS)
Testing: extent (PASS)
Testing: file_system_block_header (PASS)
Testing: inode_btree (PASS)
Testing: inode_btree_record (PASS)
Testing: inode_information (PASS)
Testing: io_handle (PASS)
Testing: notify (PASS)
Testing: superblock (PASS)
Testing: support (PASS)
Testing: volume (PASS)
PASS test_library.sh (exit status: 0)
```

`tests/test_tools.sh.log`（3 个程序全部真实执行并通过；sha256
`d12ca8faeffece4164e561859eb527abc7e57acd9c1a2c9724abbfab0104fdd7`）：

```text
Testing: info_handle (PASS)
Testing: output (PASS)
Testing: signal (PASS)
PASS test_tools.sh (exit status: 0)
```

`tests/test_fsxfsinfo.sh.log`（跳过原因逐字；sha256
`54d9b0c31fa1287095b80d5e2d4d977d8c2a73f90f7cdb20a13e4ad40b2fe426`）：

```text
Test input directory not found.
SKIP test_fsxfsinfo.sh (exit status: 77)
```

### 计数口径（两个注册面，单位不同，不混用）

| 注册面 | 被审版本 20240501 | 上游当前 HEAD（2026-09-19 取数） | 本次执行 |
|---|---|---|---|
| 程序面 `check_PROGRAMS` | **25** | **31** | 25 个全部编译并执行，25/25 PASS |
| runner 面 `TESTS`（automake 汇总） | 3 | — | `# TOTAL: 3 / PASS: 2 / SKIP: 1 / FAIL: 0` |

- 声明 **N = 31**（程序面最大值 / 上游 HEAD 下界，取数：
  `awk '/^check_PROGRAMS = /{f=1;next} f&&/^\t/{print} f&&!/^\t/{exit}' tests/Makefile.am | tr -d '\t\\' | sed '/^$/d' | wc -l`
  → 被审版本 25、`raw.githubusercontent.com/libyal/libfsxfs/main/tests/Makefile.am` 31）。
- 差额 6 项为上游 20240501 之后新增、被审版本源码树内**不存在**：
  `fsxfs_test_attributes`、`fsxfs_test_block_directory`、`fsxfs_test_directory_table`、
  `fsxfs_test_file_entry`、`fsxfs_test_file_system_block`、`fsxfs_test_tools_mount_path_string`
  → 计入 **NOT_RUN**（非失败、非跳过）。
- 本次上游计数：**TOTAL 31 = PASS 25 + FAIL 0 + SKIP 0 + NOT_RUN 6**；
  实际执行集通过率 **25/25（100%）**。
- 跳过的 `test_fsxfsinfo.sh` 是 runner 面计数（单位：shell runner），
  原因 = 上游 release archive 不含 `tests/input/` 夹具，上游脚本自身 `exit 77`（EXIT_IGNORE），
  属上游测试数据能力边界，不是构建失败；`fsxfsinfo`/`fsxfsmount` 由 conan-verify 的 L2 smoke 覆盖——
   实测命中的旗标是 **`-V`**（`fsxfsinfo -V` → `fsxfsinfo 20240501`、`fsxfsmount -V` → `fsxfsmount 20240501`，
   2 个二进制通过），不是 `--version`/`--help`（本笔记早期版本误写，W4 审计 P3-R51 已纠正）。

## test_package 证据（逐字）

```text
libfsxfs/20240501@ohpcd/stable (test package): RUN: clang test_libfsxfs.c -o test_libfsxfs \
  -I<包>/include -L<包>/lib -lfsxfs
libfsxfs/20240501@ohpcd/stable (test package): RUN: clang test_ohos.c -o test_ohos \
  -I<包>/include -L<包>/lib -lfsxfs

libfsxfs/20240501@ohpcd/stable (test package): RUN: /data/service/hnp/bin/bash -c \
  'export LD_LIBRARY_PATH=<包>/lib:$LD_LIBRARY_PATH; ./test_libfsxfs'
libfsxfs 20240501 consumer test: 9 assertions passed

libfsxfs/20240501@ohpcd/stable (test package): RUN: /data/service/hnp/bin/bash -c \
  'export LD_LIBRARY_PATH=<包>/lib:$LD_LIBRARY_PATH; ./test_ohos'
libfsxfs OHOS-specific test: 5 assertions passed
```

## 依赖版本

无外部依赖（`dependencies: []`）。15 个 libyal 组件全部由发布包内嵌子树就地编译，
不消耗制品仓的任何 `<包>/<版本>`；W0 依赖清单显式声明 `none`
（`$TASK_DIR/w0-deps.txt`，判据：`requirements()` 为空、`generate()` 无 `tool_requires`）。

## 交付物

| 产物 | 说明 |
|---|---|
| `lib/libfsxfs.so.1.0.0`（+ `.so` / `.so.1` 软链） | 共享库（`--enable-shared --disable-static`） |
| `include/libfsxfs.h` + `include/libfsxfs/{codepage,definitions,error,extern,features,types}.h` | 公共头 |
| `lib/pkgconfig/libfsxfs.pc` | pkg-config 元数据 |
| `bin/fsxfsinfo`、`bin/fsxfsmount` | 上游工具（库类型包，`package_type=library` 且未声明 `cpp_info.bindirs`，按 R38/L0k 不建 `commands.json`） |
| `share/man/man1`、`share/man/man3` | 手册页 |
| `licenses/COPYING`、`licenses/COPYING.LESSER` | LGPL-3.0-or-later |

## 验证结果

```text
上游：make check → # TOTAL: 3 / PASS: 2 / SKIP: 1 / FAIL: 0
      程序面 25/25 真实执行通过（声明 N=31，差额 6 项被审版本不存在 → NOT_RUN）
适配：Conan test_package → test_libfsxfs 9 assertions + test_ohos 5 assertions = 14/14
```

## 知识增量评估（路径 B）

本轮有可复用增量，已建草稿 `knowledge/drafts/DRAFT-E587-libyal-ohos-triplet-variance.{kv,md}`。

草稿号 **E587** 由 W4 独立审计 + 编排队列仲裁确定，判据是**git 树口径**而不是取号工具的输出
（`tools/knowledge_id.py` 的主线面扫描可能落后于主线，会把已被占用的号报成空号——该工具缺陷与
本任务的撞号经过已按容器层口径写入本工作区 `feedback/pending/2026-09-19-libfsxfs-20240501.md`）：

```sh
# 空号复核（应无输出；`grep -x` 为整词匹配）
git -C "$MAIN_REPO" ls-tree -r --name-only upstream/main -- knowledge/ \
  | grep -oE "E[0-9]{3,4}" | sort -u | grep -x E587
# 再叠加各 worktree 的 knowledge/drafts/ 新增项与 manifest 的 knowledge_ref: 行
grep -rl "E587" "$HOME/ws/worktrees"/*/knowledge/drafts/ 2>/dev/null
```

- **增量 1（流程化）**：把「OHOS 三元组」从静态规则变成**现场判定流程**——同族内 `config.sub`
  的 ohos 分支随发行版本变化（libfsxfs 20240501 `grep -c ohos` = 0，libvhdi 20251119 有），
  照抄同族先例会直接 G2 FAIL。
- **增量 2（边界反证）**：E007 写「`--build/--host` 绕过会误判为交叉编译、`AC_RUN_IFELSE`
  全部跳过」；实测该后果只在 build ≠ host 时成立，build == host 取同一 GNU 三元组时
  configure 打印 `cross compiling... no`（新生成的 `common/config.h` 含 108 个 `#define HAVE_*`）。

与既有条目的分工见 manifest `path_b.differs_from`；复现脚本落
`$HOME/tmp/libfsxfs-20240501/repro-e587-config-sub-triplet.sh`（设备可直接执行）。

另有两项**工具问题**（不属知识沉淀，落 `feedback/pending/`）：

- 语言预检把根目录的 pyfsxfs 绑定 manifest（`setup.cfg: name=libfsxfs-python`）当主体语言
  manifest，判 `mixed → env_unsupported` 假终态；真值 `c`（255/261 = 98%），与任务语言 `cpp`
  属 c↔cpp 兼容族。本任务以 `--skip-step lang-preflight --start-note …` 留痕跳过。
- `init-build` 生成的 `manifest.yaml` 模板原样带 `{software}`/`{BUILD_SYSTEM}` 占位符并把
  `status` 预填为 `published`，同时预建 ARCHIVE-SPEC 已废弃的 `packaging/` 空目录。

## 注意事项

- **不要按族照抄三元组**：本包 `config.sub` 无 ohos 分支，只有 `aarch64-unknown-linux-gnu`
  能过；`--build` 与 `--host` 必须相同，否则退化成真交叉编译。
- 上游测试在**沙箱 HOME**（`<build_folder>/upstream-test-home`）下执行，不触碰用户真实 HOME。
- `make check` 前会对 `tests/test_runner.sh` 打**运行方式**补丁（libtool `.libs/` 解析 +
  `find_binary_executable` 派发），只改测试运行方式、不改任何上游用例语义与其断言语义。
  **准确口径（W4 审计 P2-R51 纠正）**：被改动的只有 `tests/test_runner.sh` 一个文件、且改的是它的
  *运行方式*（4 处：2 处 `readlink_f` 后追加 `.libs/` 解析、2 处默认分支改为经 `find_binary_executable` 派发）；
  其余上游文件——`tests/*.c`、除 `test_runner.sh` 之外的 `tests/*.sh`、`tests/Makefile.am`——逐字节未动。
  该改动发生在 conan 的 build 目录副本内，不影响 `conandata.yml` 的源码哈希。
- 上游源码不含 `patches/`：全部平台适配内联在 `conanfile.py`（含上一条的 `test_runner.sh` 运行方式改动、
  以及 `configure` 内 `umask 077`→`022` 的构建期改写）。这是同族已合入先例的同一形态
  （`archives/l/libfsntfs/20251028`、`archives/l/libvhdi/20251119` 均内联、均无 `patches/`）；
  代价是这两处改动不进补丁评审面（W4 审计 P2-R6 / P3-R3 已记录）。
