# conan create 采信轮证据报告 — dbskkd-cdb 3.00

> **本文件替代原先随 PR 提交的 `reports/conan-create.log`**：仓库审查规则 19（`.gitcode/review-memory.md` 类别三
> 第 19 条）把 `*.log` 列为 PR 禁止文件，故原始日志不再入库；本报告是当轮原始日志的
> **逐字摘录（非全文）**：下列各行区间与原始日志逐字相同（未合并、未改写、未重排）；
> 原始日志（193 行）留存任务私有目录（PR 之外）供复核：
> `$HOME/tmp/dbskkd-cdb-3/raw-conan-create-2bccf9b.log`（日志 sha256：`a362288ad2a5c270d1c71adcaed7f71a2a31b24762a68719834495809376960b`，见文末复核命令）。
> 同目录 `conan-verify-report.md` 是工具生成的门禁摘要（保持原样，未手工编辑），其中
> 「📄 日志: …/conan-create.log」一行是该工具的固定输出，指向的日志按规则 19 不再提交，
> 对应证据以本文件为准。


## 1. 命令与环境

```bash
conan create archives/d/dbskkd-cdb/3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

- 设备：HarmonyOS PC aarch64（`os=OHOS 6.0`、`arch=armv8`）
- Conan 2.29.1（OHOS 适配版）、clang 15.0.4（`/data/service/hnp/bin/clang`）
- 采信轮前已真清缓存，并以 `cache.sqlite3` 的 `recipes`/`packages` 两表回查包名为空确认

## 2. 配方导出（原文摘录）

```
======== Exporting recipe to the cache ========
dbskkd-cdb/3.00@ohpcd/stable: Exporting package recipe: /storage/Users/currentUser/ws/wt-dbskkd-cdb-3/archives/d/dbskkd-cdb/3/conanfile.py
dbskkd-cdb/3.00@ohpcd/stable: exports: File 'conandata.yml' found. Exporting it...
dbskkd-cdb/3.00@ohpcd/stable: Calling export_sources()
dbskkd-cdb/3.00@ohpcd/stable: Copied 1 '.yml' file: conandata.yml
dbskkd-cdb/3.00@ohpcd/stable: Copied 1 '.py' file: conanfile.py
dbskkd-cdb/3.00@ohpcd/stable: Copied 1 '.patch' file: 0001-dbskkd-cdb.c.patch
dbskkd-cdb/3.00@ohpcd/stable: Exported to cache folder: /storage/Users/currentUser/.conan2/p/dbskk9d7a4d1b9d43a/e
dbskkd-cdb/3.00@ohpcd/stable: Exported: dbskkd-cdb/3.00@ohpcd/stable#d0dd16c0bd12d0830646b344c0710d9f (2026-09-11 10:25:22 UTC)
```

## 3. 构建与打包（原文摘录）

```
-------- Installing package dbskkd-cdb/3.00@ohpcd/stable (2 of 2) --------
dbskkd-cdb/3.00@ohpcd/stable: Building from source
dbskkd-cdb/3.00@ohpcd/stable: Package dbskkd-cdb/3.00@ohpcd/stable:be187fe3f087e2f59986370df4ac629377eb18c4
dbskkd-cdb/3.00@ohpcd/stable: settings: os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.cppstd=17 compiler.libcxx=libc++ compiler.version=15 build_type=Release
dbskkd-cdb/3.00@ohpcd/stable: requires: cdb/20251021#ee4e7c6e666c95f0bcc77d3ab5a5de9a:4b977264131a1c74e82bd6bb51b63cc9aadc4cfa
dbskkd-cdb/3.00@ohpcd/stable: Copying sources to build folder
dbskkd-cdb/3.00@ohpcd/stable: Building your package in /storage/Users/currentUser/.conan2/p/b/dbskk3afa5406e45c0/b
dbskkd-cdb/3.00@ohpcd/stable: Calling generate()
dbskkd-cdb/3.00@ohpcd/stable: Generators folder: /storage/Users/currentUser/.conan2/p/b/dbskk3afa5406e45c0/b/build-release/conan
dbskkd-cdb/3.00@ohpcd/stable: Generating aggregated env files
dbskkd-cdb/3.00@ohpcd/stable: Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']
dbskkd-cdb/3.00@ohpcd/stable: Calling build()
dbskkd-cdb/3.00@ohpcd/stable: Apply patch (portability): 0001 dbskkd-cdb.c dictionary path override via argv[1] or the DBSKKD_JISYO environment variable
dbskkd-cdb/3.00@ohpcd/stable: RUN: make -j1 CC="/data/service/hnp/bin/clang" COMPAT="-O3 -DNDEBUG -I/storage/Users/currentUser/.conan2/p/cdbc463168baa7e1/p/include" CDBLIB="/storage/Users/currentUser/.conan2/p/cdbc463168baa7e1/p/lib/libcdb.a"
/data/service/hnp/bin/clang -O3 -DNDEBUG -I/storage/Users/currentUser/.conan2/p/cdbc463168baa7e1/p/include  -c dbskkd-cdb.c
/data/service/hnp/bin/clang -O3 -DNDEBUG -I/storage/Users/currentUser/.conan2/p/cdbc463168baa7e1/p/include  -o dbskkd-cdb \
	dbskkd-cdb.o /storage/Users/currentUser/.conan2/p/cdbc463168baa7e1/p/lib/libcdb.a

dbskkd-cdb/3.00@ohpcd/stable: Package 'be187fe3f087e2f59986370df4ac629377eb18c4' built
dbskkd-cdb/3.00@ohpcd/stable: Build folder /storage/Users/currentUser/.conan2/p/b/dbskk3afa5406e45c0/b/build-release
dbskkd-cdb/3.00@ohpcd/stable: Generating the package
dbskkd-cdb/3.00@ohpcd/stable: Packaging in folder /storage/Users/currentUser/.conan2/p/b/dbskk3afa5406e45c0/p
dbskkd-cdb/3.00@ohpcd/stable: Calling package()
dbskkd-cdb/3.00@ohpcd/stable: package(): Packaged 2 files: dbskkd-cdb, LICENSE
dbskkd-cdb/3.00@ohpcd/stable: Created package revision 61807952f13f22d319531c4a2eb8828b
dbskkd-cdb/3.00@ohpcd/stable: Package 'be187fe3f087e2f59986370df4ac629377eb18c4' created
dbskkd-cdb/3.00@ohpcd/stable: Full package reference: dbskkd-cdb/3.00@ohpcd/stable#d0dd16c0bd12d0830646b344c0710d9f:be187fe3f087e2f59986370df4ac629377eb18c4#61807952f13f22d319531c4a2eb8828b
dbskkd-cdb/3.00@ohpcd/stable: Package folder /storage/Users/currentUser/.conan2/p/b/dbskk3afa5406e45c0/p

======== Launching test_package ========
```

## 4. test_package 执行与 31 个用例（原文摘录）

```
======== Computing dependency graph ========
Graph root
    dbskkd-cdb/3.00@ohpcd/stable (test package): /storage/Users/currentUser/ws/wt-dbskkd-cdb-3/archives/d/dbskkd-cdb/3/test_package/conanfile.py
Requirements
    cdb/20251021#ee4e7c6e666c95f0bcc77d3ab5a5de9a - Cache
    dbskkd-cdb/3.00@ohpcd/stable#d0dd16c0bd12d0830646b344c0710d9f - Cache

======== Computing necessary packages ========
Requirements
    cdb/20251021#ee4e7c6e666c95f0bcc77d3ab5a5de9a:4b977264131a1c74e82bd6bb51b63cc9aadc4cfa#4d57afb5bbb0a023d60986a7864548db - Cache
    dbskkd-cdb/3.00@ohpcd/stable#d0dd16c0bd12d0830646b344c0710d9f:be187fe3f087e2f59986370df4ac629377eb18c4#61807952f13f22d319531c4a2eb8828b - Cache

======== Installing packages ========
cdb/20251021: Already installed! (1 of 2)
dbskkd-cdb/3.00@ohpcd/stable: Already installed! (2 of 2)

======== Testing the package ========
Removing previously existing 'test_package' build folder: /storage/Users/currentUser/ws/wt-dbskkd-cdb-3/archives/d/dbskkd-cdb/3/test_package/build-release
dbskkd-cdb/3.00@ohpcd/stable (test package): Test package build: build-release
dbskkd-cdb/3.00@ohpcd/stable (test package): Test package build folder: /storage/Users/currentUser/ws/wt-dbskkd-cdb-3/archives/d/dbskkd-cdb/3/test_package/build-release
dbskkd-cdb/3.00@ohpcd/stable (test package): Generating aggregated env files
dbskkd-cdb/3.00@ohpcd/stable (test package): Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']

======== Testing the package: Building ========

======== Testing the package: Executing test ========
dbskkd-cdb/3.00@ohpcd/stable (test package): Running test()
dbskkd-cdb/3.00@ohpcd/stable (test package): RUN: /data/service/hnp/bin/bash "/storage/Users/currentUser/ws/wt-dbskkd-cdb-3/archives/d/dbskkd-cdb/3/test_package/test.sh" "/storage/Users/currentUser/.conan2/p/b/dbskk3afa5406e45c0/p/bin" "/storage/Users/currentUser/.conan2/p/cdbc463168baa7e1/p/bin"
[step] dbskkd-cdb: work directory: /storage/Users/currentUser/tmp.3k6iF5nEo4
[step] make_dict: /storage/Users/currentUser/tmp.3k6iF5nEo4/SKK-JISYO.test.cdb (2455 bytes) from SKK-JISYO.test
[step] make_dict: cdbmake input /storage/Users/currentUser/tmp.3k6iF5nEo4/SKK-JISYO.test.cdb.cdbmake (250 bytes)
[step] make_dict: /storage/Users/currentUser/tmp.3k6iF5nEo4/SKK-JISYO.alt.cdb (2162 bytes) from SKK-JISYO.alt
[step] make_dict: cdbmake input /storage/Users/currentUser/tmp.3k6iF5nEo4/SKK-JISYO.alt.cdb.cdbmake (67 bytes)
[step] dbskkd-cdb test_package: running against /storage/Users/currentUser/.conan2/p/b/dbskk3afa5406e45c0/p/bin/dbskkd-cdb
        [ok] version_request: rc=0, stdout 16 bytes match
        [ok] host_request: rc=0, stdout 9 bytes match
        [ok] end_request: rc=0, stdout 0 bytes match
        [ok] eof_request: rc=0, stdout 0 bytes match
        [ok] unknown_request_code: rc=76, stdout 0 bytes match
        [ok] malformed_request_no_space: rc=76, stdout 0 bytes match
        [ok] lookup_okuri_nasi_single: rc=0, stdout 10 bytes match
        [ok] lookup_okuri_nasi_multiple: rc=0, stdout 11 bytes match
        [ok] lookup_okuri_ari: rc=0, stdout 7 bytes match
        [ok] lookup_not_found_ascii: rc=0, stdout 13 bytes match
        [ok] lookup_not_found_multibyte: rc=0, stdout 20 bytes match
        [ok] lookup_long_key: rc=0, stdout 66 bytes match
        [ok] lookup_trailing_text_after_key: rc=0, stdout 10 bytes match
        [ok] dictionary_coverage: 10/10 fixture entries answered exactly
        [ok] dictionary_env_var: DBSKKD_JISYO alone selected the alternate dictionary (1/幹事/)
        [ok] argv_overrides_env_var: argv[1] dictionary won over DBSKKD_JISYO (1/漢字/)
        [ok] missing_dictionary_exit_code: rc=78 with no stdout
        [ok] default_dictionary_path_baked_in: upstream JISYO_FILE default present in the binary
        [ok] cdbmake_input_matches_golden: generated input identical to fixtures/SKK-JISYO.test.cdbmake
        [ok] cdb_fixture_reference_reader: cdbtest reports 10 found and 0 in every other category
        [ok] session_version_request: answer=b'dbskkd-cdb-3.00 '
        [ok] session_host_request: answer=b'novalue: '
        [ok] session_lookup_found: answer=b'1/\xe6\xbc\xa2\xe5\xad\x97/\n'
        [ok] session_lookup_not_found: answer=b'4not-in-dictionary\n'
        [ok] session_lookup_after_miss: answer=b'1/\xe6\xb0\xb4/\n'
        [ok] session_end_request_exit: rc=0 leftover=b''
        [ok] ohos_elf_aarch64_pie: type=3 (ET_DYN=3) machine=183 (AArch64=183)
        [ok] ohos_elf_codesign: .codesign section size=16384
        [ok] ohos_elf_hardening: nx=True relro=True bind_now=True df_1_pie=True
        [ok] ohos_elf_relocatable: DT_NEEDED=['libc.so'] DT_RPATH/RUNPATH=[]
        [ok] ohos_runs_minimal_env: rc=0 stdout=b'dbskkd-cdb-3.00 '
[step] dbskkd-cdb test_package summary: TOTAL=31 PASS=31 FAIL=0
[ok] dbskkd-cdb test_package: all 31 cases passed

```

## 5. 结论与产物指纹

- 测试统计（标记行，schema `TOTAL = PASS + FAIL + SKIP + NOT_RUN`）：**`TOTAL=31 PASS=31 FAIL=0`**
  - 26 个消费者协议/夹具用例（`version_request` … `cdb_fixture_reference_reader`、`session_*` 6 断言）
  - 5 个鸿蒙特有平台检查（`ohos_elf_aarch64_pie`、`ohos_elf_codesign`、`ohos_elf_hardening`、
    `ohos_elf_relocatable`、`ohos_runs_minimal_env`）
- 该轮为**干净构建轮**（含 `Copying sources to build folder`、`Calling build()`、
  `Apply patch (portability)` 1 条、`RUN: make -j1 …` 1 条），不是缓存命中轮
- 包内容：`bin/dbskkd-cdb`、`licenses/LICENSE`
- `bin/dbskkd-cdb` sha256：`62a2e57cbaa80714cdb68c56bc50e8bf526a2e07d2543ec5d7bce08cd7f5dfaa`
- 包内容聚合（排除 `conaninfo.txt`/`conanmanifest.txt`）：`5df15dae0b1a6cdb595664ccc9dec4f4cba4edde5083dfd1d8b71ff93d53698d`

> 说明：日志中出现的 recipe revision（本例 `d0dd16c0…`）会随 `conan-verify`/W3 的镜像注入形态
> 变化，不作为配方内容的稳定指纹；配方稳定性以 git 对象哈希与
> `git diff <SHA_A>..<SHA_B> -- <构建输入路径>` 输出为空为准（见 `conan-verify-supplement.md`）。

## 6. 原始日志可复核性

原始日志（按规则 19 不入库）留存于任务私有目录，任何人可在设备上复核本报告的逐字摘录
（第 2/3/4 节的摘录块首行即日志区间首行，块内空行均来自原日志本身；第 1/6 节的 `bash` 块是复核命令记录、不属日志摘录，其内空行属排版）：

```bash
# 原始日志（PR 之外）
sha256sum "$HOME/tmp/dbskkd-cdb-3/raw-conan-create-2bccf9b.log"
# -> a362288ad2a5c270d1c71adcaed7f71a2a31b24762a68719834495809376960b

# 逐字比对本报告第 2/3/4 节的摘录与原始日志对应行
sed -n '2,10p;95,124p;126,193p' "$HOME/tmp/dbskkd-cdb-3/raw-conan-create-2bccf9b.log"
```

> **覆盖范围（非全文）**：原始日志 193 行，本报告摘录第 2-10、95-124、126-193 行共 107 行
> （配方导出、构建、打包与 test_package 全段）；未摘录第 1 行（空行）、第 11-94 行
> （Input profiles 回显、依赖图与 package_id 计算、编译器选项校验）与第 125 行（空行）。
> 这些未摘录部分与本包的适配结论无关，且不包含任何测试统计或产物指纹。
