# 构建与测试证据索引 — debfoster 2.8

> 三轮证据的**完整原始日志已按 workflow 第 6.1 节逐字 fenced 留档**为
> `reports/conan-create-log.md`、`reports/conan-create-l5-round2-log.md`、
> `reports/w3-local-ci-log.md`（各自头部声明原始文件的字节数/行数/sha256 与生成命令）。
> 本文件是它们的**索引与判读说明**，另附关键行摘录与计数复核命令。
>
> 原始 `*.log` 按 `.gitcode/review-memory.md` 第 19 条「PR 中禁止的文件」不随 PR 提交。
> 下表登记的三份**本地**原始日志的字节数与 sha256，用途是**确认本地文件未被后续重跑覆盖**
> ——它**不是**「与某轮构建等价」的判据（跨轮日志不会逐字节一致，见 workflow 第 7.2 节）。

轮次与文件对应：

| 轮 | 原始日志（本地，不入库）→ 逐字留档文件 | 字节数 | sha256 | 包目录（本地） |
| --- | --- | --- | --- | --- |
| 采信轮（conan-verify G2） | `reports/conan-create.log` → **`conan-create-log.md`** | 46472 | `ef35ef54f139228d7a36ae7da3f84be931dd4bc26e0fa75004c452233dbfbb7a` | `p/b/debfo567d371d4110f/p` |
| L5 复现轮 | `reports/conan-create-l5-round2.log` → **`conan-create-l5-round2-log.md`**（**非工具默认输出名**：`conan-verify` 固定写 `reports/conan-create.log`，此文件是复现轮跑完后手工另存留档） | 46472 | `f731d5e86525bdf5aac6dadcc8d9955352b9ca71d996c240ef16d49c9424e9be` | `p/b/debfo672a3cdec7510/p`（已被后续清缓存删除） |
| W3 本地 CI 模拟 | `reports/w3-local-ci.log` → **`w3-local-ci-log.md`** | 49803 | `dcdaa830ec9bcc3c8aaa6d1b541fc39f784faf70684893b68d973162b8c31f99` | `p/b/debfoa67fa32ac0e26/p` |

> 收尾阶段在最终工作树上另做了一遍系统属性与可复算性复核（umask/mode/chmod 的原始输出、
> tarball 与 7 件打包产物的 sha256 复算、三个补丁在 pristine 树上的 dry-run、上游 N 的
> 四口径取数），原始输出见 `reports/final-sha-recheck.md`；本文件的字节数/sha256 与计数
> 复核命令在该轮亦逐条重跑，结果一致。

---

## 1. 采信轮（`conan-verify` 的 G2 干净轮）

取数命令：`conan-verify debfoster 2.8 --project-dir <worktree>`（先按 workflow 第 7.2 节四步真清缓存）

```text
92:debfoster/2.8@ohpcd/stable: Sources correctly downloaded from https://deb.debian.org/debian/pool/main/d/debfoster/debfoster_2.8.orig.tar.xz
107:debfoster/2.8@ohpcd/stable: Apply patch (portability): configure 内嵌的 config.status 以 umask 077 建立 ./confXXXXXX 临时目录；该目录在 hmdfs 上落盘为 2700 且属主不是本进程 uid，随后写 subs1.awk 报 Permission denied 使 configure 失败。改为 umask 022
108:debfoster/2.8@ohpcd/stable: Apply patch (portability): src/keepers.c 调用 open() 并使用 O_RDONLY/O_RDWR/O_CREAT 但只包含 sys/file.h；glibc 经由 sys/file.h 间接引入 fcntl.h 而 OHOS 的 musl 不引入。显式包含 fcntl.h
109:debfoster/2.8@ohpcd/stable: Apply patch (portability): etc/Makefile.am 的 install-data-local 硬编码 coreutils 的 install -d；OHOS 无 install 命令导致 make install 报 exit 127。改用 autoconf 提供的 MKDIR_P 变量并同步更新无法再生的 etc/Makefile.in
111:checking build system type... aarch64-unknown-linux-ohos
124:checking whether we are cross compiling... no
167:checking for GC_malloc in -lgc... yes
181:debfoster/2.8@ohpcd/stable: RUN: make -j1
469:debfoster/2.8@ohpcd/stable: RUN: make check -j1
475:make[1]: Nothing to be done for 'check'.
479:make[1]: Nothing to be done for 'check'.
483:make[1]: Nothing to be done for 'check'.
486:make[1]: Nothing to be done for 'check-am'.
584:debfoster/2.8@ohpcd/stable (test package): RUN: /data/service/hnp/bin/bash /storage/Users/currentUser/ws/wt-debfoster-2.8/archives/d/debfoster/2.8/test_package/test.sh
622:HMBS_TEST_SUMMARY discovered=36 passed=36 failed=0 skipped=0
```

复核命令（在完整日志上实跑，计数应与上文一致）：

```sh
grep -c "Apply patch (portability)" reports/conan-create.log   # 3
grep -c "Nothing to be done for 'check'" reports/conan-create.log   # 3
grep -c 'check-am' reports/conan-create.log                          # 1
grep -c 'HMBS_TEST_SUMMARY discovered=36 passed=36 failed=0 skipped=0' reports/conan-create.log  # 1
```

## 2. L5 复现轮

取数命令：真清缓存（workflow 第 7.2 节四步）后重跑与采信轮相同的 `conan create`
（`-pr:h`/`-pr:b` 同 profile、`--build=missing --user=ohpcd --channel=stable`），
跑完把 `reports/conan-create.log` 手工另存为本表登记的
`reports/conan-create-l5-round2.log`（该文件名不是任何工具的默认输出）。
逐产物 sha256 比对见 `conan-verify-supplement.md` §6.2。

```text
106:debfoster/2.8@ohpcd/stable: Calling build()
107:debfoster/2.8@ohpcd/stable: Apply patch (portability): configure 内嵌的 config.status 以 umask 077 建立 ./confXXXXXX 临时目录；该目录在 hmdfs 上落盘为 2700 且属主不是本进程 uid，随后写 subs1.awk 报 Permission denied 使 configure 失败。改为 umask 022
108:debfoster/2.8@ohpcd/stable: Apply patch (portability): src/keepers.c 调用 open() 并使用 O_RDONLY/O_RDWR/O_CREAT 但只包含 sys/file.h；glibc 经由 sys/file.h 间接引入 fcntl.h 而 OHOS 的 musl 不引入。显式包含 fcntl.h
109:debfoster/2.8@ohpcd/stable: Apply patch (portability): etc/Makefile.am 的 install-data-local 硬编码 coreutils 的 install -d；OHOS 无 install 命令导致 make install 报 exit 127。改用 autoconf 提供的 MKDIR_P 变量并同步更新无法再生的 etc/Makefile.in
181:debfoster/2.8@ohpcd/stable: RUN: make -j1
469:debfoster/2.8@ohpcd/stable: RUN: make check -j1
475:make[1]: Nothing to be done for 'check'.
479:make[1]: Nothing to be done for 'check'.
483:make[1]: Nothing to be done for 'check'.
486:make[1]: Nothing to be done for 'check-am'.
584:debfoster/2.8@ohpcd/stable (test package): RUN: /data/service/hnp/bin/bash /storage/Users/currentUser/ws/wt-debfoster-2.8/archives/d/debfoster/2.8/test_package/test.sh
622:HMBS_TEST_SUMMARY discovered=36 passed=36 failed=0 skipped=0
```

## 3. W3 本地 CI 模拟

取数命令（`ohc` 包在 `scripts/` 下，须显式给出 `PYTHONPATH`）：

```sh
cd <worktree>
PYTHONPATH=scripts python3 -c \
  "from ohc.workflow_checks import run_local_ci; run_local_ci('debfoster', '2.8', '.')"
```

```text
1:$ setup.sh (RC=0)
15:$ build_and_test.sh archives/d/debfoster/2.8 (RC=0)
23:G0_RESULT=pass
99:  [done] Pre-downloaded 1 files, conandata.yml updated to file:// URLs
171:debfoster/2.8: Calling source() in /storage/Users/currentUser/.conan2/p/debfo1c30c4915b19f/s
172:debfoster/2.8: Sources correctly downloaded from file:///storage/Users/currentUser/ws/wt-debfoster-2.8/.build-cache/predl_cache/86b8c49b_debfoster_2.8.orig.tar.xz
664:debfoster/2.8 (test package): RUN: /data/service/hnp/bin/bash /storage/Users/currentUser/ws/wt-debfoster-2.8/archives/d/debfoster/2.8/test_package/test.sh
702:HMBS_TEST_SUMMARY discovered=36 passed=36 failed=0 skipped=0
719:L0_RESULT=pass: all checks passed
720:L1_RESULT=pass: upstream tests + test_package executed
721:L2_RESULT=pass: debfoster --version OK
722:L4_RESULT=pass: patches clean
723:L5_RESULT=pass: bin/ has content
733:[step] Pre-download: conandata.yml 已还原为官方 URL
```

> 注：本仓 CI 的门禁集是 `G0/L0/L1/L2/L4/L5`（`ci/conan/build_and_test.sh` 只发这几个
> `*_RESULT`，全仓无 `L3` 定义），因此没有 `L3` 行属正常，不是漏跑。

## 4. 依赖 flags 与编译配置的取证行

`conan-verify-supplement.md` §6.2 的「编译命令行含依赖 `-I`」与 §6.1 的
`build-tree 副本 == 打包副本`判据都引用了编译行，此处摘录两轮的对应行（均在第 187 行）：

```text
/data/service/hnp/bin/clang -DHAVE_CONFIG_H -DVAR=\"//var\" -DETC=\"//etc\" -DLOCALEDIR=\"//share/locale\" -I. -I/storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src   -DNDEBUG -I/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/include -Wall -O3 -MT AVLTree.o -MD -MP -MF $depbase.Tpo -c -o AVLTree.o /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/src/AVLTree.c &&\
```

```text
/data/service/hnp/bin/clang -DHAVE_CONFIG_H -DVAR=\"//var\" -DETC=\"//etc\" -DLOCALEDIR=\"//share/locale\" -I. -I/storage/Users/currentUser/.conan2/p/b/debfo672a3cdec7510/b/src   -DNDEBUG -I/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/include -Wall -O3 -MT AVLTree.o -MD -MP -MF $depbase.Tpo -c -o AVLTree.o /storage/Users/currentUser/.conan2/p/b/debfo672a3cdec7510/b/src/AVLTree.c &&\
```

两行都含 `-I/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/include`（`AutotoolsDeps`
注入的 `gc` 依赖 include，DRAFT-E2186 的修复面）与 `-DNDEBUG`；两轮均**无** `-g`
（这正是 §6.2「无 DWARF `DW_AT_comp_dir` 漂移」判据的依据）。

取数命令：

```sh
grep -n 'clang -DHAVE_CONFIG_H' reports/conan-create.log | head -1
grep -n 'clang -DHAVE_CONFIG_H' reports/conan-create-l5-round2.log | head -1
```

## 5. 完整原始日志的可获取性

三份原始日志都由工具在本地重新生成（`conan-verify`、W3 的 `run_local_ci()`），
任一轮的权威外部证据是 PR 的 CI 构建页（如 `https://ohpcd.atomgit.com/ci?id=44325`）；
此外上表记录的**字节数与 sha256** 可用于判断某次重跑是否与本文摘录出自同一轮。
