# krb5-sync 3.1 适配笔记

## 编译环境
- 构建系统: autotools（上游 configure + Makefile.in；Conan 2.29.1，AutotoolsToolchain/AutotoolsDeps，basic_layout）
- 编译日期: 2026-09-26
- 编译器: /data/service/hnp/bin/clang；profile ci/conan/profiles/ohos-aarch64（host 与 build 同 profile，真交叉 --host=aarch64-linux-ohos --build=x86_64-linux-gnu）
- 构建主机: B 机（HarmonyOS aarch64 8 核/31G，W3 与全部实测均出自该机），worktree ~/qzy/主理-68-krb5-sync-3.1（自 主理-64 树按交接移交），分支 feat/krb5-sync-3.1
- CONAN_HOME: ~/tmp/ch/home-z68-krb5fix2（P1-2「同轮残留恢复」棒的全新 home；只从已验证的 home-z68-krb5fix 复制 global.conf 与 remotes.json 播种，不复用其构建缓存。上一轮整改棒在用的 home-z68-krb5fix 与只读取证棒的 home-krb5-sync 本棒一律不写）
- 依赖: krb5/1.22.1、openldap/2.6.7（均为 ohpcd 已发布制品，真实下载二进制）；本轮实际落点 ~/tmp/ch/home-z68-krb5fix2/p/krb50acf73e42647a/p 与 .../p/openla04925142be38/p，conan-verify 的 build 目录 .../p/b/krb5-1cc022442ede1/b/build-release、W3 的 build 目录 .../p/b/krb5-e8bc842af190e/b/build-release
- 状态: built

## 判决与实测读数（reports/ 不入 git，本节是唯一对外证据面）

### conan-verify（第 6 轮：加「同轮残留恢复」后重跑，全新 home）
命令: python3 scripts/ohc-run.py conan-verify krb5-sync 3.1（其 G2 就是一次干净的 conan create）
  G2 命令原文（verify-r1.log 第 13 行区段）: conan create archives/k/krb5-sync/3.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=同一 profile --build=missing --user=ohpcd --channel=stable
VERIFY_RC=0；runner-verify.out 第 13 行「VERIFY_RC=0」，verify-r1.log 第 23 行「✅ 配方验证通过: krb5-sync 3.1」、第 24 行「可标记 status: published」
runner 日志: ~/tmp/uc2/krb5-p12/verify-r1.log（26 行）与 runner-verify.out；同轮 GATE_PASS MemAvailable=6267MB（runner-verify.out 第 10 行）、build-slot 短槽 SLOT_OK 17:30:14（verify-r1.log 第 3 行）
reports/conan-verify-report.md（48 行，sha256 effe7ee263d849b2ae65c1079a3d176afe440a5df351f2358c95a9f40c92533a）第 3 行「**Verdict**: PASS」；第 6 行 Date 2026-09-26T18:55:06.216396
分项（同报告行号）: 8 G0 PASS、17 G1 PASS、31 G2 PASS、35 G3 PASS、38 G4 PASS、41 L2 PASS、44 L4 PASS、47 L5 PASS
G0 段第 15 行仍打印建议语「⚡ G2 conan create 可能因此失败，建议先修复」（命中 E490）；判决只认节行 ⇒ 第 31 行 G2 实测 PASS，非阻塞提示，未据此改配方
G4/L2/L4/L5 打印「无法找到程序包 ID / 跳过（无 cache 路径）」是 conan-verify 单跑的形态（四节仍判 PASS），执行类判定以本节 G2 与下面 W3 一节为准
reports/conan-create.log 本轮被 finish 内部的 create（18:55:02）覆盖为 147 行（sha256 756bfbde0c659f964d88d06f8a91cea612cba3a35a4aca6a000244004e3c16df；该次 create 命中缓存、build() 未重跑，故只剩消费者三行：第 136 行 cmake --build test_package、第 143 行「Executing test」、第 146 行「krb5-sync ran (rc=1)」）。**同轮 17:32 的 verify 版（536 行）里 make check 判决在第 423/424 行、残留恢复在第 425/428/429 行**，该版本已被覆盖、行号不可再从盘上复算 ⇒ 对外判定以下面被 log_sha256 锁住的 w3-local-ci.log 为准（消费者断言非 126/127 ⇒ 判通过）



### W3 本地 CI 模拟（第 6 轮重跑，配方 build() 内 make check 真执行 + 同轮残留恢复）
命令: sh ~/tmp/uc2/build-slot.sh --kind short -- python3 scripts/ohc-run.py finish krb5-sync 3.1 built
runner 日志: ~/tmp/uc2/krb5-p12/finish-r1.log（129 行）与 runner-finish.out；同轮短槽 SLOT_OK 18:54:32（finish-r1.log 第 3 行）
  ⚠ 本机当时被别的窗口压满：gate.sh 默认门槛 MemAvailable≥6000MB 连续 40 轮 GATE_RC=1（实测 5.2~5.4GB），18:54:31 降到空闲后才 GATE_PASS ⇒ **排队等到准入才起构建，没有放宽门槛、没有绕闸**
  第 57 行: "✅ 本地 CI 模拟通过 (日志: /storage/Users/currentUser/qzy/主理-68-krb5-sync-3.1/archives/k/krb5-sync/3.1/reports/w3-local-ci.log)"
  第 58 行: "✅ W3 本地 CI 模拟通过"
  第 103 行「失败步骤: step5b, step8」、第 116 行「EXIT_REASON: finish_success」、FINISH_RC=2（step5b/step8 是文档/知识完整性侧，非 W3；W3 判定见上两行与 .ci-result.json）
reports/w3-local-ci.log: sha256 = 3f7ef752a995cb635949f728ed37f630aa4c572bbdc673594f250c7b983ec252
  字节数 73771、行数 634、mtime 2026-09-26 18:58:53；"\[step\]" 计数 47；"_RESULT=" 计数 9
.ci-result.json（逐字）: "timestamp": "2026-09-26T18:58:53.183487"、"exit_code": 0、"step": "W3_local_ci"、"integrity_hash": "7864d0bf21335b01"、"log_sha256": "3f7ef752a995cb635949f728ed37f630aa4c572bbdc673594f250c7b983ec252" ⇒ 与实算 sha256 逐字相同（互锁成立）
判决行（同日志行号）: 23 G0_RESULT=pass、66 KC_RESULT=pass、93 JC_RESULT=pass、620 L0_RESULT=pass: all checks passed、621 L1_RESULT=pass: upstream tests + test_package executed、622 L2_RESULT=skip: krb5-sync version/help failed, krb5-sync-backend failed、623 L4_RESULT=pass: patches clean、624 L5_RESULT=pass: bin/ has content
  第 606/607/608 行 L1a/L1b/L1c（L1c 原文 "[ok] L1c: Upstream official tests (make check/ctest) executed in build phase"）⇒ 本轮 L1 的"上游测试已执行"是真执行判据，不是吞掉后的默认绿
  第 490 行 "krb5-sync/3.1: make check rc=2"、第 491 行 "krb5-sync/3.1: make check summary: Aborted 7 test sets, passed 1180/1250 tests, 1 test skipped."、第 492 行残留清除自证、第 495 行 "ERROR: queue hygiene: plugin/queuing ran 47 assertions and 5 failed -- Failed 5/47 tests, 89.36% okay."、第 496 行 "KRB5_QUEUE_HYGIENE_RESULT=set=plugin/queuing discovered=1 executed=47 failed=5 passed=42 declared=47 rc=1" ⇒ 判决原文与「上游测试申报」一节逐字一致
  消费者断言（同日志）: 第 599 行 "======== Testing the package: Executing test ========"、第 602 行 "krb5-sync ran (rc=1)"（非 126/127 ⇒ 判通过）
⚠ L2_RESULT=skip（step5b/step8 与 FINISH_RC=2 同理）是框架侧存量现象，不计 W3 红；W3 判决只认 .ci-result.json 的 exit_code=0 与 runner 第 57/58 行


## 链接墙：取证、根因与复算

### 一手取证（第 2 轮失败日志原文）
第一条真实错误: libtool: link: cannot find the library '//lib/liblber.la' or unhandled argument '//lib/liblber.la'
连锁: make[1]: "*** [Makefile:891: plugin/sync.la] Error 1" → make: "*** [Makefile:739: all] Error 2"
失败链接行（摘录）: -module -avoid-version -L.../openla04925142be38/p/lib ... -o plugin/sync.la -rpath //lib/krb5/plugins/kadm5_hook ... -lldap -llber -lkrb5 ...
依赖包内 .la 三行原文:
  openldap liblber.la: library_names='liblber.so.2.0.200 liblber.so.2 liblber.so' / inherited_linker_flags='' / libdir='//lib'
  openldap libldap.la: library_names='libldap.so.2.0.200 libldap.so.2 libldap.so' / inherited_linker_flags='' / dependency_libs=' -L/storage/Users/currentUser/usr/local/lib //lib/liblber.la' / libdir='//lib'
  krb5 包内无任何 .la（find 无 libkrb5.la）；同目录实际存在 liblber.so/.2/.2.0.200 与 libldap.so/.2/.2.0.200
钉死的根因: 产生 //lib 的字符串是 **openldap 制品 .la 内记录的 libdir='//lib'** 与 libldap.la 的 dependency_libs 绝对项 //lib/liblber.la（openldap 自身以 --prefix=/ 构建）；libtool 对可见 .la 的优先级高于同目录 .so，于是沿用了这条已搬迁的绝对路径（前一行还打印 "library ... was moved" 警告）。本包 --prefix=/ 归一化出的 -rpath //lib 是**同一成因的第二处字符串**，但不是 cannot find 的来源。

### 所选修法（conan-recipe 侧，缓存零改动）
依 knowledge/graph/E236.kv:29 的 rec_approach=scoped-la-free-static-archive-directory，并守 knowledge/graph/E236.kv:47 的 forbid_1（不删、不 sed 依赖缓存里的 .la）：
1) 新增 _la_free_dep_libdir()：把 openldap libdir 内**非 .la** 载荷镜像进 build 私有目录 .la-free-libs；
2) 新增 _point_build_env_at_mirror()：在 conan 生成件里把 -L 与 --with-ldap-lib 一并指向镜像（AutotoolsDeps 把 -L 写进 build-release/conan/conanautotoolsdeps.sh 的 LDFLAGS，configure 再抄进 config.status 与 Makefile ⇒ 事后改 Makefile 会被 config.status 还原，必须落在生成件上、configure 之前）；
3) --with-ldap-lib 传镜像目录；4) _extra_configure_args() 追加 --libdir=/lib，消掉本包自产的 //lib（工具链默认 --libdir 为 prefix 串接 /lib；安装仍走 DESTDIR ⇒ 包内布局不变）；5) make 之前加 E236 guard：生成的 Makefile 对 openldap libdir 命中数必须为 0，否则抛 ConanException 点名文件。

### 复算读数（第 6 轮 W3 重跑后按新日志行号更新）
grep -c "//lib" reports/w3-local-ci.log = 0；grep -c "cannot find the library" = 0；grep -c getcwd = 0
E236 三条自证行（新 w3-local-ci.log）: 189 镜像 6 个 .so、194 redirect 命中 conanautotoolsdeps.sh/conanbuild.conf/conanrunenv-release-armv8.sh、374 guard 0 hits；E386 探壳行 195（/bin/sh rc=0 stderr=<empty> -> accepted）
plugin/sync.la 与制品链接成功（同日志）: 428/429 plugin/sync.la -> plugin/.libs/sync.so（-rpath /lib/krb5/plugins/kadm5_hook）、484/485 tools/krb5-sync；本轮 W3 create 的 build 目录是 krb5-e8bc842af190e，conan-verify G2 的是 krb5-1cc022442ede1（同一 home-z68-krb5fix2 下的两个独立 build 缓存）
⚠ reports/conan-create.log 会被下一轮 create 覆盖（本轮再次实证：17:32 的 536 行版被 18:55 的 147 行版覆盖），对外判定以 w3-local-ci.log 的 sha256 为准


## 另外两处交付形状修正（本棒，一手取证）
1) package_info 增 cpp_info.includedirs = []：本包安装集无公开头文件（制品只有 bin/krb5-sync、bin/krb5-sync-backend、lib/krb5/plugins/kadm5_hook/sync.so、licenses/LICENSE、share/man/man8/*.8），保留默认 include 目录会让 CMakeDeps 的 INTERFACE_INCLUDE_DIRECTORIES 指向不存在的路径，test_package 在 cmake.configure() 就炸（第 3 轮 G2 即因此红，原文 Imported target "krb5-sync::krb5-sync" includes non-existent path .../p/include）。
2) bindirs 与 runenv 从 sbin 改 bin：工具链把 sbindir 定为 prefix/bin ⇒ 上游"装到 sbin"的两个命令行工具实际落在 bin/；test_package/conanfile.py 原先取 sbin/krb5-sync，会让 test.c 的 access(KRBSYNC_BIN, X_OK) 假失败。

## 上游测试申报（本包上游确有测试，不得申报 0）

### 本轮真跑判决（2026-09-26 18:57，B 机 aarch64，配方 build() 内 make check 真执行 + 同轮残留恢复）
全量 make check 的 runtests 摘要两行原文（构建主机侧日志 .../p/b/krb5-e8bc842af190e/b/build-release/make-check.log 第 177 / 178 行，181 行、sha256 c21ee0c42f8c2c77ffec79acb16b826d91a08decc53c24a73ee00b293ca01975；同一判决由配方打印进 reports/w3-local-ci.log 第 491 行）:
```
Aborted 7 test sets, passed 1180/1250 tests, 1 test skipped.
Files=17,  Tests=1250,  0.98 seconds (0.27 usr + 0.29 sys = 0.56 CPU)
```
同轮残留恢复跑（plugin/queuing）摘要原文（同目录 make-check-queuing.log 第 7 / 8 行，8 行、sha256 d5a8e8b3007c75bd94c1bf36f30114fbf4801894e9a38728a8338d341efcc4f9；配方自证行见 reports/w3-local-ci.log 第 495/496 行）:
```
plugin/queuing..FAILED 6, 13, 19, 25, 32
Failed 5/47 tests, 89.36% okay.
Files=1,  Tests=47,  0.05 seconds (0.01 usr + 0.03 sys = 0.04 CPU)
KRB5_QUEUE_HYGIENE_RESULT=set=plugin/queuing discovered=1 executed=47 failed=5 passed=42 declared=47 rc=1
```

### 数字口径（两套分开写，不混用）
- `N_registered`（登记在册的测试集数）= **17**：上游 tests/TESTS 实 17 行 = 11 个本机编译出的 C 测试二进制（10 个 tests/**/*-t.c 驱动 + tests/util/xmalloc）+ 6 个 perl/pod 驱动集（docs/pod、docs/pod-spelling、perl/critic、perl/minimum-version、perl/strict、tools/backend）。
- `N_static`（runtests 自报展开出的断言总数）= **1250**（上面 Files= 行的 Tests=1250）；全量 make check 本轮 **passed 1180**、**skipped 1**、其余未通过（1250−1180−1=69）。失败表列 plugin/queue-only 23/23 与 plugin/queuing 47/47 合计 70，与 69 相差 1 条，该差落在 runtests 自己对 aborted 集的计数口径内 ⇒ **本文件原样引用 runtests 读数，不做推算调整**。
- **恢复跑口径（本轮新增，只影响 plugin/queuing 一集）**：该集在全量 pass 里 0 执行（ABORTED），删掉同轮残留后单独重跑，runtests 自报 `Files=1, Tests=47`、`Failed 5/47 tests` ⇒ **该集实测执行 47 条、通过 42 条、失败 5 条、rc=1**。合并后的五维读数：静态声明 1250（=17 集展开）/ 登记 17 集 / **有执行证据 1180+47=1227 条**（全量 pass 的 1180 + 恢复跑的 47）/ 未执行 23 条（plugin/queue-only MISSED 1-23，崩溃所致，runtests 失败表按 23/23 计未通过）+ 6 集 perl/pod 各 0 条 / **判失败 5 条**（全在 plugin/queuing，见下节根因）/ skipped 1 条（util/xmalloc 作者限定）/ 消费者测试 1 条。⛔ 恢复跑的 47 条**不折进** `Files=17, Tests=1250` 那两行原文，两套读数分开列，避免把同一条链的两次判定混成一个分母；也⛔ 不把"未执行的 23"与"执行了但判假的 5"混写成同一类。
- ⛔ 17 是「测试集/文件」数、不是用例总数，不得拿它当 `N_static` 申报（上一版 assertion_count: 17 正是这个口径错误）。
- 适配后 test_package 消费者断言 = **1** 条（test.c：access(KRBSYNC_BIN, X_OK) + fork/execl --help 且 rc 不为 126/127；本轮 w3-local-ci.log 第 599 行「Executing test」→ 第 602 行「krb5-sync ran (rc=1)」⇒ 判通过）。
- 申报合计 = `N_static` 1250 + test_package 1 = **1251**（断言口径）；登记口径 = 17 + 1 = **18**（测试集/文件口径）。**未通过项一律不计入通过。**

### 逐集结果（make-check.log 第 148–164 行判决 + 第 166–175 行失败表，17 集全列）
| TESTS 登记集 | runtests 判决（原文） | Fail/Total | Stat | 一手原因 |
|---|---|---|---|---|
| docs/pod | ABORTED (execution failed -- not found?) | 0/0 | 101 | perl/pod 驱动集，本机无该解释器（能力面，0 断言） |
| docs/pod-spelling | ABORTED (execution failed -- not found?) | 0/0 | 101 | 同上 |
| perl/critic | ABORTED (execution failed -- not found?) | 0/0 | 101 | 同上 |
| perl/minimum-version | ABORTED (execution failed -- not found?) | 0/0 | 101 | 同上 |
| perl/strict | ABORTED (execution failed -- not found?) | 0/0 | 101 | 同上 |
| plugin/heimdal | ok | — | — | Heimdal kadmin hook 接口集全通过 |
| plugin/mit | ok | — | — | MIT kadmin hook 接口集全通过 |
| plugin/queue-only | MISSED 1-23 (killed by signal 11, core dumped) | 23/23 | -- | **未通过**，根因见下一节（上游测试数据的 GNU sed 假设） |
| plugin/queuing | 全量 pass：ABORTED (cannot mkdir queue: File exists)（47/47, stat 255）；同轮恢复跑：FAILED 6, 13, 19, 25, 32（5/47, stat 0） | 恢复跑 5/47 | 恢复跑 rc=1 | 全量 pass 里 **0 执行**（上一集崩溃留下的 tests/tmp/queue）；删残留后单独重跑 **47 条真执行、42 通过、5 失败**，5 条失败是文件模式断言，根因见下一节（与 queue-only 的 SIGSEGV 不是同一条因） |
| portable/asprintf | ok | — | — | 全通过 |
| portable/mkstemp | ok | — | — | 全通过 |
| portable/reallocarray | ok | — | — | 全通过 |
| portable/snprintf | ok | — | — | 全通过 |
| tools/backend | ABORTED (execution failed -- not found?) | 0/0 | 101 | perl/pod 驱动集，本机无该解释器（能力面，0 断言） |
| util/messages | ok | — | — | 全通过 |
| util/messages-krb5 | ok | — | — | 全通过 |
| util/xmalloc | skipped (xmalloc tests only run for author) | — | — | 作者限定 skip（上游自身判定，非本包放宽），计 1 条 skipped |

统计（全量 pass）：**ok 8 集、skipped 1 集、aborted 7 集（含 plugin/queuing）、崩溃 1 集（plugin/queue-only 23 条断言未执行）**，合计 17 集。
统计（含同轮恢复跑）：**1 集（plugin/queuing）由 0 执行变为 47 条真执行** ⇒ ok 8 集、恢复跑部分通过 1 集（42/47）、skipped 1 集、aborted 5 集（全是 perl/pod 驱动，各 0 断言）、崩溃 1 集未执行；**没有任何集被跳过或删除，分母仍是 runtests 自报的 1250**。

### 未通过集的一手根因（引同机只读取证棒结论；本棒未自行定性、未改上游）
取证件: ~/tmp/uc2/z68-krb5/queue-only-forensics.md（只读取证棒 2026-09-26 16:46 落盘；§2 定性结论、§3 可处置性、§4 自述未查项）
- **plugin/queue-only 的 23 条 SIGSEGV 不写成「平台限制」**：上游 tests/data/make-krb5-conf 第 38 行使用 GNU sed 扩展 `sed 0,/^ *krb5-sync *= */d`；HarmonyOS PC 上唯一可用的 sed 是 toybox 0.8.12——**接受该表达式、输出 0 字节却返回 0**，测试于是拿到 210 字节的截断 krb5.conf（缺 `[libdefaults]`），走到上游 plugin/config.c 的 !HAVE_KRB5_REALM 分支时 free_default_realm(NULL) 解引用 NULL+8 ⇒ SIGSEGV（一手 SEGV_MAPERR@0x8、帧 sync_config_string+0x50，取证棒称与源码/反汇编逐条对得上）。
- **plugin/queuing 与它是同一条「残留」链、但 5 条失败是另一条独立因**：queue-only 崩在 rmdir(queue) 之前 ⇒ $BUILD/tmp/queue 残留 ⇒ 紧随的 queuing 无条件 mkdir(queue) 报 `Bail out! cannot mkdir queue: File exists`（exit 255），全量 pass 里该集 **0 执行**。本轮在配方里加了「同轮残留恢复」（make check 之后删 tests/tmp/queue、单独重跑该集），实测该集 47 条全部执行：**42 通过、5 失败、rc=1**；5 条全是同一句 `...mode of queue file is correct`（断言 6/13/19/25/32，`is_int(0600, st.st_mode & 0777)`，实测 seen=416 即 0640）。
- **那 5 条失败的一手定性（本棒实测，非取证棒推定）**：插件在 plugin/queue.c:268 用 `open(path, O_WRONLY|O_CREAT|O_EXCL, 0600)` 建队列文件，本机构建文件系统把创建模式改写成 **0640**；直接探针复现 3/3 次：`os.open(..., 0o600)` → 实际 0640、`os.open(..., 0o700)` → 实际 0740，**且随后 `chmod(0o600)` 也清不掉 group-read（3/3 次仍 0640）**，同目录内探针同样复现；当时 umask=022（0600 & ~0022 = 0600，与观测相反 ⇒ 不是 umask，也不是本包权限设置）。⇒ 该 5 条是「平台文件模式语义与上游断言不一致」，⛔ 不得写成 queue-only 那条 GNU-sed 崩溃链的级联，也⛔ 不得笼统写成「环境不支持」。
- ⛔ 更正一处旧申报：上一节（P1-1 棒）写「取证棒在干净副本单跑 queuing 得 **rc=0**（42 ok + 5 not ok 权限）」——本棒在同一台机、同一 profile、删净 $BUILD/tests/tmp 后单独重跑实测 **rc=1**（`Failed 5/47 tests, 89.36% okay.`，见 make-check-queuing.log 第 7 行），42 ok + 5 not ok 的部分与取证棒一致；rc=0 是误记，已按实测替换。
- 取证棒并已**排除「配方产物形状」这一归因**：Makefile.am 把插件源码直接编进测试可执行文件，这两集不 dlopen 插件、不看 plugin/sync.la、与 --libdir=/lib 及 package() 删 .la 无关；HAVE_KRB5_REALM 的探测结果经头文件核实为正确判定。
- **本棒仍不动上游测试源码**（⛔ 改 tests/data/make-krb5-conf 的 GNU-only sed、⛔ 跳用例、⛔ 放宽断言、⛔ 缩小分母）：queue-only 那 23 条要救必须改上游测试数据，属用户/主理裁决项；queuing 那 5 条要救必须放宽上游 `is_int(0600, ...)` 断言或改插件的建文件语义，同样不在本棒范围。本棒做的只有「测试卫生」——让因同轮崩溃而 0 执行的一集真正跑起来并逐条申报。取证棒自述「补丁后的 CI 口径未实测」（其 §4）。
- 另 6 集 perl/pod 驱动 aborted 属设备能力面（无 perl 解释器，贡献 0 条断言）。

### 已试过的失败方案
1. **裸 `make check`（第 3 棒及以前的形状）**：check 环境没把 Conan 依赖库目录放进 LD_LIBRARY_PATH ⇒ runtests 与驱动全部 `Error loading shared library libgssapi_krb5.so.2`，`check-local` 以 **rc=127** 收（旧 w3 日志 636–648 行原文）。本轮改为在配方里内联 `LD_LIBRARY_PATH=<全部 requires 的 libdirs>`（conanfile.py build() 段）后，**同一台机、同一 profile、同一依赖制品**直接跑到 runtests 摘要 ⇒ 归因确认为「check 环境缺库路径」，旧注释「目标二进制跑不动」是错的。
2. **`try: autotools.make(target=check) / except Exception: info(...)` 的 catch-all 守卫**（独立 W4 P1 W4-68-01）：吞掉一切失败（含真实编译/链接失败）且 create 仍以 0 退出，与旧注释「a genuine compile failure still aborts」自相矛盾；被引先例 krb5-strength/3.3 的措辞是有条件的（still aborts wherever execution works）。本轮删除，改为**窄判据**：make check 走 ignore_errors=True 并重定向到 build_folder/make-check.log，只有抓到 runtests 的 `Aborted ` / `Files=` 摘要行才算过，否则抛 ConanException（＝测试框架根本没跑起来就交付）。
3. **申报「真机原生全量运行、以 CI 结果为准」而无任何执行背书**（独立 W4 P1 W4-68-02）：本轮起三处载体（本节 / test_package/MANIFEST.yml / 版本级 manifest.yaml 的 platform.limitations）一律换成上面两行 runtests 原文与逐集表；`关联 Issue` 与路径两行按 B 判定=hit 落定（见下一节）。
4. **把 17 当成用例总数申报**：旧 assertion_count: 17 与旧「上游 17 + test_package 1 = 18」正是该口径错误；本轮拆成 `N_static`=1250 与 `N_registered`=17 两套分开写。
5. **「在 make check 之前先清一次 tests/tmp/queue」**（本轮否证，故恢复放在 check 之后）：残留目录是**同一次 make check 内部**由 plugin/queue-only 崩溃留下的，check 前清掉的那个目录会被本次运行重新造出来。一手时间戳：本轮 W3 的 build-release/make-check.log mtime 18:57:26.853、build-release/tests/tmp/queue 在同一次运行后仍存在（配方第 492 行自证删除它），删除后 1 秒内（make-check-queuing.log mtime 18:57:27.525）该集就跑到 47 条真执行 ⇒ 卫生动作只能跟在崩溃之后，不能排在 check 之前。

### 静态计数（第 1 棒四式实读数，本棒沿用；与上面的实测口径不是一回事）
*-t.c 驱动 10、tests/runtests.c 1、tests/TESTS 17 行、tests/data 7 项、demo 与 examples 0、上游 tar 条目 141；make -n check 355 行（旧棒读数，存 ~/tmp/uc2/z64-krb5-sync/make-n-check.log）。


## 交付与路径声明
适配路径: 主路径 A（Conan 配方 + 2 个上游补丁），**B 判定=hit**（主理终判）——机制全部命中既有 knowledge/graph 条目，本 PR 不新建知识库扩展、不建 Issue、不携带 knowledge/drafts 成对草稿
使用知识库: knowledge/graph/E236.kv:29 与 knowledge/graph/E236.kv:47、knowledge/graph/E386.kv:31（capability-tested-shell-and-selective-dispatch）、knowledge/graph/E122.kv（config.sub kernel-os 先例）
知识库扩展: 无（B 判定=hit）——下文「发现与知识」节的 K1–K9 是对既有 E236/E386/E122/E011/E129 机制的**命中与复算记录**，不是新增机制，故不作为本 PR 的 B 交付物计数
关联 Issue: 无（B 判定=hit，本 PR 不携带 knowledge/drafts 成对草稿、不建知识库扩展 Issue）

## 对话 #1（第 1 棒：领取与取证）
领取 krb5-sync/3.1；核对 conandata 源哈希 b26918d7564e1c03b8ca392ffdf882cfa201789e54a97ed00f043a082a92814e；四式静态计数上游测试（10/1/17/7，demo 与 examples 0，tar 141 条）；按 knowledge/graph/E122.kv 做 config.sub 的 linux-ohos 放行（补丁 0001）与 configure mktemp 的 umask 022（补丁 0002，hunk 头 @@ -18389,12 +18389,12 @@）；生成交付形状骨架与 commands.json。

## 对话 #2（第 2 棒：getcwd 墙与 configure 段）
判出 configure: error: working directory cannot be determined 的真因是 profile buildenv 的 CONFIG_SHELL/SHELL 指向 /data/service/hnp/bin/bash 在 HMDFS 上 getcwd 坏；按 knowledge/graph/E386.kv:31 加 _pick_shell()（rc=0 且 stderr 为空且输出绝对路径才收），并把 TMPDIR/CONFIG_SHELL/SHELL 内联前缀在显式 sh configure 上（不走 os.environ、不用 Environment().define），make 传 -j1 SHELL=探得壳；configure 段过墙，卡点转移到 libtool 链接。

## 对话 #3（第 3 棒＝本棒：链接、W3 与对外文本）
钉死 //lib 取证（依赖 .la 三行 + 失败链接行）→ 按 knowledge/graph/E236.kv 做 la-free 镜像 + 生成件重定向 + --libdir=/lib + E236 guard；补 includedirs/bindirs/test_package 三处交付形状；conan-verify 三一致转绿；build-slot 短槽内跑完 finish 拿到 W3（.ci-result.json exit_code=0、log_sha256 与实算一致）；重写本 notes 与两份 manifest 占位。

## P1-2 棒（2026-09-26 17:2x–18:5x，本棒）：同轮残留恢复（测试卫生）
上一轮申报里 plugin/queuing 在全量 pass 里 0 执行（同轮 queue-only 崩溃留下的 tests/tmp/queue），本棒只做「让它真跑起来并逐条申报」这一件事，⛔ 不动上游测试源码、⛔ 不跳用例、⛔ 不放宽断言、⛔ 不改分母。
1) 只读确认 runtests 支持位置参数单跑一集：`./runtests -h` 用法首行 `Usage: %s [-hv] [-b <build-dir>] [-s <source-dir>] <test> ...`，且 tests/runtests.c:1526-1565 走 `build_test_list(argv, argc)` + `test_batch()`；全量 pass 的调用形态是 make-check.log 第 143 行 `cd tests && ./runtests -l <source>/tests/TESTS`。⇒ 恢复跑用 `cd tests && ./runtests plugin/queuing`，同 LD_LIBRARY_PATH 内联前缀（缺它即 rc=127）。
2) 配方 build() 末尾增量加 _recover_queuing_residue()：只有全量日志真出现 `plugin/queuing...cannot mkdir queue` 才触发；删残留后校验目录确实消失，再单独重跑该集；恢复跑自带窄判据——取不到该集判决或 Files=/Tests= 读数、判决是 ABORTED/MISSED/skipped、summary 分母与 plan 不一致都抛 ConanException，⛔ 静默吞掉。已有的「全量摘要取不到就 raise」守卫原样保留（恢复跑排在它之后，即"先证明框架跑起来过再谈恢复"）。
3) 本机实测（W3 同轮）：该集 47 条真执行、42 通过、5 失败、rc=1，5 条全是 `...mode of queue file is correct`；单独探针复现"创建模式 0600 → 实际 0640、chmod 也清不掉"（3/3），据此把上一轮「干净副本单跑得 rc=0」的误记按实测更正，并把这 5 条与 queue-only 的 23 条 SIGSEGV 分成两条独立因。
4) 三件套在**全新 home-z68-krb5fix2** 重跑：conan-verify VERIFY_RC=0（G0-G4/L2/L4/L5 全 PASS）、finish W3 exit_code=0 且 log_sha256 与实算逐字相同；gate.sh 因 MemAvailable 5.2~5.4GB 连续 40 轮拒绝，排队到 18:54:31 才准入（未放宽门槛、未绕闸、未占长杆槽）。
5) 本地对配方新分支做过 6 例干跑（用真机日志原文喂：FAILED/ABORTED/skipped/无摘要/全绿/未触发），判决与 raise 行为符合上述判据。

## 发现与知识

✅ [K1] knowledge/graph/E236.kv:29 的 la-free 处置在"依赖只装 .so、且 .la 的 dependency_libs 写成绝对 //lib/liblber.la"这一形态下同样成立：镜像目录只收非 .la 载荷即可摘掉不可搬迁元数据，缓存零改动（对照 knowledge/graph/E236.kv:47 的 forbid_1）。
✅ [K2] 重定向必须落在 conan 生成件上：AutotoolsDeps 把依赖 libdir 写进 build-release/conan/conanautotoolsdeps.sh 的 LDFLAGS，configure 再抄进 config.status 与 Makefile ⇒ 事后 sed Makefile 会被 config.status 还原。
✅ [K3] --prefix=/ 会让本包自产 //lib 字符串（libtool -rpath 与自身 .la 元数据）；追加 --libdir=/lib 后 -rpath 变 /lib/krb5/plugins/kadm5_hook，而 DESTDIR 安装布局不变（制品仍是 lib/krb5/plugins/kadm5_hook/sync.so）。
✅ [K4] 无公开头文件的插件包必须显式 cpp_info.includedirs = []，否则 CMakeDeps 的 INTERFACE_INCLUDE_DIRECTORIES 指向不存在的 include/ 目录，test_package 在 cmake.configure() 阶段就红。
✅ [K5] Conan 工具链把 sbindir 定为 prefix/bin ⇒ 上游"装 sbin"的工具实际在 bin/；test_package 与 runenv_info 照抄 sbin 会造成 access()/PATH 假失败。
✅ [K6] knowledge/graph/E386.kv:31 的探壳判据（rc=0 且 stderr 为空且输出绝对路径）在本 HMDFS 构建目录上把 /data/service/hnp/bin/bash 判退、/bin/sh 判收（W3 重跑后同日志第 195 行读数），configure 段的 getcwd 墙随之消失
✅ [K7] 上游 2012 版 build-aux/config.sub 要在 maybe_os 分支放开 linux-ohos 并从 -linux-ohos* 拒绝表摘除，补丁 0001 的 hunk 头为 @@ -115,8 +115,8 @@ 与 @@ -1376,7 +1376,7 @@；先例 knowledge/graph/E122.kv 的锚点行（第 2 棒上报 config.sub 第 118 与 1379 行、直拿先例补丁报 Hunk 1 FAILED 1754/1754）在本快照不成立 ⇒ 锚点必须按快照自制，编号先例只搬机制。
✅ [K8] configure 的 mktemp 辅助在 HMDFS 上必须以 umask 022 运行，否则建出的临时目录 drwx--S--- 拒绝探针写入（补丁 0002）。
✅ [K9] 框架 verify 输出的"详细文档"正文与命中的 E 编号可能不同源（本次打印命中 E386 而正文实为 CMake 符号链接那条），故本包一律只按 knowledge/graph/E236.kv 与 knowledge/graph/E386.kv 原文办事；该缺陷已由主理入表。
⚠ [K10]（P1-2 棒实测，**未做 B 判定、不在本 PR 计 B 交付**）本机构建文件系统在创建文件时会把模式 0600 改写成 0640、0700 改写成 0740，且随后 `chmod(0600)` 也无法清掉 group-read（同目录探针 3/3 复现，umask=022 时 0600 & ~0022 仍是 0600 ⇒ 与 umask 无关）。任何断言"新建文件必须恰好 0600"的上游测试在此类文件系统上恒失败——plugin/queuing 的 5 条 `...mode of queue file is correct` 就是这一条，不是 queue-only 崩溃链的级联。是否升路径 B 由主理判定，本棒只留实测载体（make-check-queuing.log 第 1/5/7 行 + w3-local-ci.log 第 495/496 行）。

## 交付物
| 文件 | 说明 |
|------|------|
| bin/krb5-sync | 队列消费端命令行工具（R38：软件级 commands.json 已登记） |
| bin/krb5-sync-backend | 向 AD/kadmin 回放的执行端工具 |
| lib/krb5/plugins/kadm5_hook/sync.so | kadmin 钩子插件，由 kadmin 运行期 dlopen（故 cpp_info.libs 为空） |
| licenses/LICENSE | BSD-3-Clause |
| share/man/man8/krb5-sync.8、krb5-sync-backend.8 | 上游手册页 |

## 注意事项
运行期前提：krb5-sync-backend 需要可用的 kadmin/AD 侧配置，本包只做构建与消费者级可执行验证（test_package 用 --help 探可执行性），未做真实 AD 联测；L2 平台功能矩阵报 skip（version/help 两个探针失败）属该工具无 --version 且 help 需配置的形态，未放宽任何判据。
---

**编译结束**: 2026-09-26 18:54
**最终状态**: built
