# libfsapfs 20240429 适配笔记

## 编译环境

- 构建系统：autotools（发布包自带生成好的 `configure` / `aclocal.m4` / `config.guess` / `config.sub` / `Makefile.in`）
- 编译日期：2026-09-20
- 编译器：`clang` / `clang++` 15.0.4（OHOS SDK，`/data/service/hnp/bin/clang`），profile `ci/conan/profiles/ohos-aarch64`（`os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.version=15 build_type=Release`）
- 解释器：`CONFIG_SHELL=/data/service/hnp/bin/bash`（设备无 `/bin/bash`，`/bin/sh` 是 toybox）
- 并发：`-c tools.build:jobs=2`（设备 `os.cpu_count()`=20 而 affinity=8，见配方 `build()` 里的 `jobs = min(conf, 4)`）
- 状态：built

## 源码溯源

本包与同批「上游仓库被重置」的同族包**情况相反**：libyal 的 libfsapfs 仓库
`20240429` 的 tag 与官方 release 资产**都还在**，因此固定源用**官方 release 资产**
（R39 官方源头口径），不需要回落到发行版镜像：

```text
$ git ls-remote --tags https://github.com/libyal/libfsapfs
c9ec39f755f6e9df9c49cbd51df658eab93da941	refs/tags/20240429
31bbef14f5cc927820d170fb52b181dbf39d1193	refs/tags/20260917

$ curl -sS 'https://api.github.com/repos/libyal/libfsapfs/releases/tags/20240429'
tag: 20240429 | assets: ['libfsapfs-experimental-20240429.tar.gz', 'libfsapfs-experimental-20240429.tar.gz.asc']

$ curl -sS -o /dev/null -w '%{http_code}\n' -L \
    https://github.com/libyal/libfsapfs/releases/download/20240429/libfsapfs-experimental-20240429.tar.gz
200
```

三面互证（两个独立来源 + 逐字节比对）：

```text
$ sha256sum libfsapfs-experimental-20240429.tar.gz libfsapfs_20240429.orig.tar.gz
665f70705e69ce90c87e0f9c185d47002e242b79b0a37ae52751cdfa8363a538  libfsapfs-experimental-20240429.tar.gz
665f70705e69ce90c87e0f9c185d47002e242b79b0a37ae52751cdfa8363a538  libfsapfs_20240429.orig.tar.gz
$ cmp -s <两条 URL 的下载件> && echo IDENTICAL_BYTES
IDENTICAL_BYTES
$ head -c 2 libfsapfs-experimental-20240429.tar.gz | od -An -tx1
 1f 8b
$ gzip -t libfsapfs-experimental-20240429.tar.gz && echo GZIP_OK
GZIP_OK
$ tar tzf libfsapfs-experimental-20240429.tar.gz | head -2
libfsapfs-20240429/
libfsapfs-20240429/libfdata/
```

- Debian PGP 签名 `libfsapfs_20240429-1.dsc` 的 `Checksums-Sha256` 独立锚定同一哈希
  （`665f70705e69ce90c87e0f9c185d47002e242b79b0a37ae52751cdfa8363a538 2171864 libfsapfs_20240429.orig.tar.gz`），
  两条 URL 的下载件 `cmp` **逐字节一致**；
- 文件大小 2171864 字节，顶层目录 `libfsapfs-20240429/`。

展开后是**自包含闭包**：17 个 bundled libyal 组件
（`libbfio libcaes libcdata libcerror libcfile libclocale libcnotify libcpath libcsplit
libcthreads libfcache libfdata libfdatetime libfguid libfmos libhmac libuna`）
与生成好的 Autotools 文件全部在包内。配方 `build()` 早期校验该闭包，缺失即报
`ConanInvalidConfiguration` 并拒绝走 `synclibs.sh`。

## 三元组选型

本包自带的 `config.sub`（2024）**没有 ohos 分支**，现场取证：

```text
$ grep -c ohos config.sub
0
$ ./config.sub aarch64-unknown-linux-ohos ; echo rc=$?
rc=1
$ ./config.sub aarch64-unknown-linux-gnu ; echo rc=$?
aarch64-unknown-linux-gnu
rc=0
```

故用 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`（**两者取同一三元组**），
configure 打印 `checking whether we are cross compiling... no`，`AC_RUN_IFELSE` 正常执行。
这与同族 `libfsxfs/20240501`（同为 2024 版）一致，而与 `libvhdi/20251119`（2025 版接受
`linux-ohos`）相反——**三元组必须现场取证、不能按族照抄**（另见知识草稿
`DRAFT-E587-libyal-ohos-triplet-variance`）。

## 依赖与可选特性（本轮的核心判读）

发布包自包含，**Conan 侧无外部依赖**（`w0-deps.txt` 显式声明 `none`）。但 libyal 的
`configure.ac` 还会**自动探测**两个外部可选能力，读数必须自己看，不能按同族先例照抄：

```text
checking for zlib >= 1.2.5... no          ← 只是 pkg-config 没有 zlib.pc
checking for zlib.h... yes                ← 真正的结论在这三行
checking for zlibVersion in -lz... yes
checking for uncompress in -lz... yes
checking for openssl >= 1.0... no
checking for openssl/opensslv.h... no
checking for openssl/evp.h... no
```

configure 摘要（逐字，`sed -n '/^Building:/,/^Features:/p' configure.log`）：

```text
   DEFLATE compression support:                 zlib
   libhmac support:                             local
   MD5 support:                                 local
   SHA256 support:                              local
   libcaes support:                             local
   AES-ECB support:                             local
   AES-XTS support:                             local
   FUSE support:                                no
```

判读：**zlib 有**（来自 OHOS NDK sysroot，设备与 CI 用同一 SDK，非设备特供）；
**libcrypto 没有，但加密能力没有丢**——AES-ECB/AES-XTS 与 MD5/SHA256 由发布包内嵌的
`libcaes`/`libhmac` 提供（摘要显示 `local`）。因此本包**不**照抄 `libfvde`/`libbde` 的
`--with-openssl=no`，保持 auto-detect，配方 `configure_args` 只有
`--disable-python` / `--with-libfuse=no` / `--enable-static-executables=no` + 三元组。

zlib 来源取证（clang 默认 include 搜索路径）：

```text
$ /data/service/hnp/bin/clang -E -v -x c /dev/null 2>&1 | sed -n '/search starts here/,/End of search list/p'
 /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include
 /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/aarch64-linux-ohos
 /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include
```

另一条必须知道的边界（m4 源码逐字，本包自带）：`--disable-shared`（静态）时
`AX_ZLIB_CHECK_LIB` / `AX_LIBCRYPTO_CHECK_LIB` 的第一行会把两个能力**无条件置 no**，
configure 不报错——静态包会静默失去压缩/加密能力。本包用 `shared=True`（默认），不受影响。

```m4
m4/zlib.m4      : [test "x$ac_cv_enable_shared_libs" = xno || test "x$ac_cv_with_zlib" = xno],
                  [ac_cv_zlib=no],
m4/libcrypto.m4 : [test "x$ac_cv_enable_shared_libs" = xno || test "x$ac_cv_with_openssl" = xno],
                  [ac_cv_libcrypto=no],
```

## 平台适配（全部内联在 conanfile.py，无 patches/）

1. **HMDFS 的 `umask 077` 不可用** → 构建期把 `configure` 内的 `umask 077` 改为 `022`，
   并全程 `os.umask(0o022)`（同族先例 E011）。
2. **HMDFS 禁止直接执行源码树脚本 / 设备无 `/bin/bash`** → 用
   `CONFIG_SHELL=/data/service/hnp/bin/bash` 解释 `configure`，并给 `make check` 传
   `LOG_COMPILER`（同族先例 E087）。
3. **平台三元组** → 自带 `config.sub`（2024）无 ohos 分支，显式传
   `--build/--host=aarch64-unknown-linux-gnu`（见上「三元组选型」）。
4. **沙箱 HOME** → 上游测试在 `<build_folder>/upstream-test-home` 下执行，
   不触碰用户真实 HOME。
5. **测试驱动方式不做任何改动** → 上游 `make check` 原样驱动（见下一节：libtool 包装脚本
   在本设备可以直接执行，第一版配方准备的 runner 补丁是空操作，已删除）。

### test_runner.sh 与 libtool 包装脚本：**本包未做任何补丁**

第一版配方照抄了同族 `libfsxfs/20240501` 的做法，准备把 `tests/test_runner.sh` 的两个默认
执行分支接到它自带的 `find_binary_executable()`（把 libtool 包装脚本解析成 `.libs/` 真实 ELF）。
**现场实测证明这一步在本设备上是空操作，故最终配方删掉了它**，理由与依据：

```text
# 1) 该 helper 的解析判据是 GNU file 的 "POSIX shell script" 措辞
$ file -b <某 libtool 包装脚本>
/bin/sh script                     ← 设备上 file 是 toybox 0.8.12，措辞不同
$ file -b <包装脚本> | grep -c "POSIX shell script"
0                                  ← 判据不成立 → helper 原样返回包装脚本路径

# 2) 包装脚本本身可以直接执行（HMDFS 不拦脚本 exec）
$ printf '#!/bin/sh\necho ran-directly\n' > wrap.sh && chmod 755 wrap.sh && ./wrap.sh
ran-directly
rc=0
```

`$TASK_DIR` 下同口径的复现命令（审计者可原样执行）：

```sh
mkdir -p "$TASK_DIR/probe-exec" && cd "$TASK_DIR/probe-exec"
printf '#!/bin/sh\necho ran-directly\n' > wrap.sh && chmod 755 wrap.sh
file -b wrap.sh                                  # → /bin/sh script
file -b wrap.sh | grep -c "POSIX shell script"   # → 0
./wrap.sh                                        # → ran-directly, rc=0
```

留一个无效补丁等于在 PR 里写一条**未经证实**的适配理由，因此删除它、让上游 runner
原样工作；被审版本的 `tests/test_runner.sh` 与本包其余上游文件一样**逐字节未改**。
（若某个环境里的 `file` 确实输出 POSIX shell script，该 helper 会解析到 `.libs` ELF，
配方为 `make check` 与两个直跑程序都准备了 `LD_LIBRARY_PATH`，两种形态都能跑。）

### 未被任何 runner 驱动的 2 个 check_PROGRAMS（不计入执行数，现场探针已留证）

`tests/test_library.sh` 驱动 52 项、`tests/test_tools.sh` 驱动 7 项，合计 59 项；
`tests/Makefile.am` 注册的 61 项里剩下的
`fsapfs_test_data_block_vector`、`fsapfs_test_volume_superblock` **不被任何上游 runner 驱动**。

第一版配方曾把这两个程序直接跑起来「补全覆盖」，**采信轮实测证明这个做法是错的**：
`fsapfs_test_data_block_vector` 独立直跑即失败（G2 FAIL，逐字）：

```text
libfsapfs/20240429@ohpcd/stable: RUN: .../tests/.libs/fsapfs_test_data_block_vector
fsapfs_test_data_block_vector.c:96 result (-1) != 1
Unable to run test: libfsapfs_data_block_vector_initialize
ConanException: Error 1 while executing
```

根因在**上游测试自身与实现不同步**（不是平台问题）：该用例调用
`libfsapfs_data_block_vector_initialize(&vector, io_handle, NULL, NULL, 0, &error)`
并期望返回 1，而当前实现明确把 `data_handle == NULL` 判为无效参数返回 -1
（`libfsapfs/libfsapfs_data_block_vector.c:86-96`：`if( data_handle == NULL ) … invalid data handle … return( -1 )`）。
上游从不把这两个程序列入任何 runner，所以这处陈旧从未被发现。

两个程序在设备上的独立探针读数（`LD_LIBRARY_PATH=<build>/libfsapfs/.libs`，逐字）：

```text
$ ./.libs/fsapfs_test_data_block_vector ; echo rc=$?
fsapfs_test_data_block_vector.c:96 result (-1) != 1
Unable to run test: libfsapfs_data_block_vector_initialize
rc=1
$ ./.libs/fsapfs_test_volume_superblock ; echo rc=$?
rc=0
```

**处置**：为不改动上游的测试执行面、也不出现「只挑通过的那一个来跑」的口径，
两个无 runner 驱动的注册项**一律不计入本次执行数**，按 NOT_RUN 申报并各自给出上面的
原始读数（一个失败、一个通过，都如实写在这里）。配方里因此**没有**任何直跑步骤，
`make check` 就是全部测试动作。

## 语言判定（R47）

`lang-preflight` 判出 `mixed → env_unsupported`，属**本族已知的工具假阳性**（同批
libfsxfs/libfvde/libfsfat 三次独立复现，本包为第 4 次）。人工逐份核验根目录三份 manifest：

```text
setup.cfg      : name = libfsapfs-python / description = Python bindings module for libfsapfs
setup.cfg.in   : 同上（@VERSION@ 占位）
pyproject.toml : 只有 [build-system] requires = ["setuptools","wheel"] / build-backend = "setuptools.build_meta"
setup.py       : 首行注释 "Script to build and install Python-bindings."
```

即三者都只是 **`pyfsapfs` Python 绑定模块**的打包 manifest，不是主体语言 manifest；
源码 341 个文件中 `.c` 333（98%）、`.py` 4（`setup.py` + 3 个 `tests/pyfsapfs_test_*.py`）、
`.cc` 4（全部是 `ossfuzz/*_fuzzer.cc` 模糊测试夹具）、`.sh` 8（`tests/*.sh` 驱动 + `ltmain.sh`）。
按 R47 附录 D.4「绑定类包按源码主体判」，主体语言为 C，与任务语言 `cpp` 属 c↔cpp 兼容族。
据此 `--skip-step lang-preflight --start-note "<理由>"` 继续适配；readiness 记 **skip（非通过）**。

## 编译步骤

```sh
# 1) 采信轮（清缓存 → 8 道门禁 → 证据三副本 → finish 前快照）
sh tools/conan_verify_round.sh libfsapfs 20240429 --repo "$TARGET_REPO" --task-dir "$TASK_DIR"

# 2) 收尾与复核
#    finish <软件> <版本> built → tools/finish_restore.sh --apply
#    → python3 tools/capture_evidence.py --verify "$TASK_DIR/evidence-index.json"
```

## 上游测试证据（逐字）

> `reports/` 被 `.gitignore` 覆盖，**不进 PR 提交面**；PR 正文引用的同一批逐字证据在本节。
> 原始 `.log` 只留任务私有目录（`$TASK_DIR/evidence-manual/`）与 conan 构建目录，
> 按 AGENTS §2「不将运行期日志入库」不入提交面。

### 取数命令

```sh
B=<conan build folder>/b          # 本次：/storage/Users/currentUser/.conan2/p/b/libfs84b7b45b9cd8c/b
cat   "$B/tests/test-suite.log"
grep -c ' (PASS)$' "$B/tests/test_library.sh.log" "$B/tests/test_tools.sh.log"
cat   "$B/tests/test_fsapfsinfo.sh.log" "$B/tests/test_fsapfsinfo_bodyfile.sh.log"
```

### `tests/test-suite.log`（automake 汇总，runner 面）

```text
==============================================
   libfsapfs 20240429: tests/test-suite.log
==============================================

# TOTAL: 4
# PASS:  2
# SKIP:  2
# XFAIL: 0
# FAIL:  0
# XPASS: 0
# ERROR: 0
```

### `tests/test_library.sh.log`（52 个程序，全部 PASS）

```text
Testing: bit_stream (PASS)
Testing: btree_entry (PASS)
Testing: btree_footer (PASS)
Testing: btree_node (PASS)
Testing: btree_node_header (PASS)
Testing: buffer_data_handle (PASS)
Testing: checkpoint_map (PASS)
Testing: checkpoint_map_entry (PASS)
Testing: checksum (PASS)
Testing: chunk_information_block (PASS)
Testing: container_data_handle (PASS)
Testing: container_key_bag (PASS)
Testing: container_reaper (PASS)
Testing: container_superblock (PASS)
Testing: compressed_data_handle (PASS)
Testing: compression (PASS)
Testing: data_block (PASS)
Testing: data_block_data_handle (PASS)
Testing: data_stream (PASS)
Testing: deflate (PASS)
Testing: directory_record (PASS)
Testing: encryption_context (PASS)
Testing: error (PASS)
Testing: extended_attribute (PASS)
Testing: extent_reference_tree (PASS)
Testing: file_extent (PASS)
Testing: file_system (PASS)
Testing: file_system_btree (PASS)
Testing: file_system_data_handle (PASS)
Testing: fusion_middle_tree (PASS)
Testing: huffman_tree (PASS)
Testing: inode (PASS)
Testing: io_handle (PASS)
Testing: key_bag_entry (PASS)
Testing: key_bag_header (PASS)
Testing: key_encrypted_key (PASS)
Testing: name (PASS)
Testing: name_hash (PASS)
Testing: notify (PASS)
Testing: object (PASS)
Testing: object_map (PASS)
Testing: object_map_btree (PASS)
Testing: object_map_descriptor (PASS)
Testing: profiler (PASS)
Testing: snapshot (PASS)
Testing: snapshot_metadata (PASS)
Testing: snapshot_metadata_tree (PASS)
Testing: space_manager (PASS)
Testing: volume (PASS)
Testing: volume_key_bag (PASS)
Testing: container (PASS)
Testing: support (PASS)
PASS test_library.sh (exit status: 0)
```

> `container` 与 `support` 是 `LIBRARY_TESTS_WITH_INPUT` 里的两个程序：发布包没有
> `tests/input/`，`test_library.sh` 按自身的 `if test -d "input"` 分支**改走无参直跑**
> 并通过（这两个不是 SKIP——SKIP 的只有下面两个 fsapfsinfo runner）。

### `tests/test_tools.sh.log`（7 个程序，全部 PASS）

```text
Testing: bodyfile (PASS)
Testing: digest_hash (PASS)
Testing: info_handle (PASS)
Testing: mount_path_string (PASS)
Testing: output (PASS)
Testing: path_string (PASS)
Testing: signal (PASS)
PASS test_tools.sh (exit status: 0)
```

### 两个 SKIP 的 runner（上游规则，`exit 77`）

```text
$ cat tests/test_fsapfsinfo.sh.log
Test input directory not found.
SKIP test_fsapfsinfo.sh (exit status: 77)

$ cat tests/test_fsapfsinfo_bodyfile.sh.log
Test input directory not found.
SKIP test_fsapfsinfo_bodyfile.sh (exit status: 77)
```

### 清点取数（两个注册面，单位不同，不混用）

```sh
# 程序面：被审版本 20240429
awk '/^check_PROGRAMS = /{f=1;next} f&&/^\t/{print} f&&!/^\t/{exit}' tests/Makefile.am \
  | tr -d '\t\\' | sed '/^$/d' | wc -l                       # → 61
# 程序面：上游当前 HEAD（声明 N 的下界，2026-09-20 取数）
curl -sSL https://raw.githubusercontent.com/libyal/libfsapfs/main/tests/Makefile.am \
  | awk '/^check_PROGRAMS = /{f=1;next} f&&/^\t/{print} f&&!/^\t/{exit}' \
  | tr -d '\t\\' | sed '/^$/d' | wc -l                       # → 63
# runner 面：automake TESTS
sed -n '/^TESTS = /,/^$/p' tests/Makefile.am                 # → 4 个脚本（python 绑定已 --disable-python）
```

被审版本 61 与上游 HEAD 63 的差额（NOT_RUN，被审版本树内不存在）：

```text
fsapfs_test_file_entry
fsapfs_test_key_bag_value
```

### 计数汇总（与 manifest.yaml 的 `tests:` 段同源）

```text
声明 N（上游 HEAD 下界）      = 63
被审版本注册                  = 61
  被上游 runner 驱动并实跑     = 59   （test_library.sh 52 + test_tools.sh 7）
  注册但无 runner 驱动         = 2    （data_block_vector / volume_superblock，NOT_RUN，探针读数见上）
被审版本树内不存在            = 2    （file_entry / key_bag_value，NOT_RUN）
TOTAL 63 = PASS 59 + FAIL 0 + SKIP 0 + NOT_RUN 4
runner 面（另一单位）          : TOTAL 4 = PASS 2 + SKIP 2 + FAIL 0
```

## test_package 证据（逐字）

```text
libfsapfs 20240429 consumer test: 10 assertions passed
libfsapfs OHOS-specific test: 5 assertions passed
```

- 通用消费者（`test_libfsapfs.c`，10 项）：版本串 `20240429`、`get_access_flags_read`、
  `get_codepage` 正常/错误路径、`set_codepage`、`check_container_signature(NULL)` 与
  `check_volume_signature(NULL)` 错误路径、`container_initialize`、`container_free`
- 鸿蒙专项（`test_ohos.c`，5 项，`#ifndef __OHOS__ #error`）：编译目标、`TMPDIR` 非 `/tmp`、
  临时路径构造、临时文件写读往返比对、清理后 `access()` + `errno == ENOENT`


## 交付物

- `lib/libfsapfs.so.1.0.0`（含 `.so`/`.so.1` 软链）、`include/libfsapfs.h` 及头文件目录
- `lib/pkgconfig/libfsapfs.pc`、`share/man/man1|man3`、`licenses/COPYING{,.LESSER}`
- 包内含 `bin/fsapfsinfo`、`bin/fsapfsmount` 两个上游工具；配方未声明 `cpp_info.bindirs`，
  按 R38/L0k 以**库类型**处理，不新增 `commands.json`（同族先例 libfsntfs/libvhdi）。

## 知识增量评估（路径 B）

新增草稿 `knowledge/drafts/DRAFT-E590-libyal-optional-dep-autodetect-ohos.{kv,md}`：

- **主题**：libyal 家族外部可选依赖（zlib/libcrypto）在 OHOS 上的**探测读数判据**与
  「静态构建静默关闭能力」假绿面；明确「缺 libcrypto ≠ 缺加密」（内嵌 libcaes/libhmac 提供
  AES/MD5/SHA256），以及**不要按族照抄 `--with-openssl=no`**。
- **为何不重复**：`E277` 管发布包**内嵌**组件的闭包完整性；本条管**外部可选依赖**的探测与取舍留痕；
  `E007`/`E011`/`E087`/`E228` 分别管三元组/umask/CONFIG_SHELL/libtool `.libs`，本条只引用其结果。
- **取号**：编排方预留 `E590`；按容器层口径以 **git 树**为判据复核为空号
  （`git -C "$TARGET_REPO" ls-tree -r --name-only upstream/main -- knowledge/ | grep -oE "E[0-9]{3,4}" | sort -u | grep -x E590` → 无输出），
  并留痕跑一次 `tools/knowledge_id.py --check E590 --fresh`（同样报未占用；该结论**不作为判据**）。

## 注意事项

- 本包**不修改任何上游测试用例，也不修改测试驱动**：`tests/*.c`、`tests/*.sh`、
  `tests/Makefile.am` 逐字节未动，`make check` 按上游原样驱动（见上文
  §「test_runner.sh 与 libtool 包装脚本：本包未做任何补丁」）。
- 证据逐字转 `.md`：`reports/` 被 `.gitignore` 覆盖不进 PR，PR 正文引用的逐字证据在本文件。
- 上游 `tests/input/` 夹具不在发布包内 → `test_fsapfsinfo.sh` / `test_fsapfsinfo_bodyfile.sh`
  按上游自身规则 `exit 77`（SKIP），不是构建失败。
