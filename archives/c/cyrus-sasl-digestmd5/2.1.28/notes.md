# cyrus-sasl-digestmd5 2.1.28 适配笔记

## 编译环境

- 目标平台: HarmonyOS PC / OpenHarmony aarch64（`os=OHOS`、`arch=armv8`、clang 15.0.4）
- 构建系统: autotools（configure + make，in-source 构建）
- 上游: https://github.com/cyrusimap/cyrus-sasl tag `cyrus-sasl-2.1.28`
- 源码: `cyrus-sasl-2.1.28.tar.gz`，sha256 `7ccfc6abd01ed67c1a0924b353e526f1b766b21f42d4562ee635a8ebfc5bb38c`
- 依赖: `openssl/3.5.6`（唯一强制第三方依赖）
- 适配日期: 2026-09-26
- 状态: built

## 版本口径

| 环节 | 值 | 证据 |
|---|---|---|
| 请求名 | `cyrus-sasl-digestmd5` 2.1.28（**机制子包名**，非 Debian 源包名） | madison 查询 `cyrus-sasl-digestmd5` 空结果；`cyrus-sasl2` → 2.1.28+dfsg1-11 |
| 源包 | `cyrus-sasl2`（Debian） | sources.debian.org API |
| 上游工程/版本 | Cyrus SASL `2.1.28` | `configure.ac:51 AC_INIT([cyrus-sasl],[2.1.28],…)` |
| 机制归属 | `libdigestmd5.so`（DIGEST-MD5；Debian control: "DIGEST-MD5 (with DES support, deprecated)"） | `debian/control` libsasl2-modules |

## 依赖提取（真实构建文件）

```
plugins/Makefile.am:97   libdigestmd5_la_SOURCES = digestmd5.c digestmd5_init.c
plugins/Makefile.am:99   libdigestmd5_la_LIBADD = $(LIB_DES) $(LIB_SOCKET) $(COMPAT_OBJS) $(PLUGIN_COMMON_OBJS)
configure.ac:337         SASL_DES_CHK
configure.ac:340         AC_ARG_ENABLE(digest, … [yes])
configure.ac:362-367     if test "$enable_static" = yes; then
                           SASL_STATIC_SRCS="$SASL_STATIC_SRCS $(top_srcdir)/plugins/digestmd5.c"
                           SASL_STATIC_OBJS="$SASL_STATIC_OBJS digestmd5.o"  ; AC_DEFINE(STATIC_DIGESTMD5,…)
m4/kerberos_v4.m4:18-27  AC_CHECK_LIB(crypto, des_cbc_encrypt, [AC_CHECK_HEADER(openssl/des.h,
                           [AC_DEFINE(WITH_SSL_DES,…) LIB_DES="-lcrypto"; with_des=yes], with_des=no)], with_des=no, $LIB_RSAREF)
                          同段再以 DES_cbc_encrypt 复测一次（openssl≥1.1 的 des_* 是宏，真实符号为大写 DES_*）
m4/openssl.m4            --with-openssl=DIR → CPPFLAGS += -I<DIR>/include、CMU_ADD_LIBPATH(<DIR>/lib)
plugins/digestmd5.c:61-75  #ifdef WITH_DES / #ifdef WITH_SSL_DES / #include <openssl/des.h>
plugins/digestmd5.c:855-1117  #ifdef WITH_DES … des_key_sched / des_cbc_encrypt / des_ede2_cbc_encrypt
```

结论：**唯一第三方依赖 = openssl/3.5.6**。W（同源树 libsasl2/plugin_common/内部 MD5/内部 RC4）、S（libc/libdl）、T（autoconf/make/clang）不计入。

## 编译步骤（真实命令）

```bash
# 0) 源码获取与三方 sha256 核验（下载产物 sha256 == 仓内 8 份同族 recipe 记录；plugins/digestmd5.c 与 .dep-analysis git-archive 内容一致）
# 1) init-build（--project-dir 指向本 worktree）
python3 $SKILL_ROOT/scripts/ohc-run.py init-build cyrus-sasl-digestmd5 2.1.28 --url=<官方 release tarball> --project-dir <wt>
# 2) 补丁（由 refresh-patch --auto 生成，见下）
# 3) 真实构建 / 配方执行
conan create archives/c/cyrus-sasl-digestmd5/2.1.28 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="cyrus-sasl-digestmd5/*"
```

configure 关键参数（与同族 login/gssapiv2 一致的静态最小闭包）：

```
--prefix=/ --disable-dependency-tracking --disable-sample --enable-digest --with-openssl=<openssl包目录>
--disable-shared --enable-static --without-staticsasl --disable-staticdlopen
--disable-anon --disable-cram --disable-plain --disable-scram --disable-gssapi --disable-httpform
--disable-krb4 --disable-ldapdb --disable-login --disable-ntlm --disable-otp --disable-passdss
--disable-sia --disable-sql --disable-srp --disable-srp-setpass
--without-saslauthd --without-authdaemond --without-gdbm --without-ldap --without-mysql --without-opie
--without-pam --without-pgsql --without-pwcheck --without-sqlite --without-sqlite3
--disable-auth-sasldb --with-dblib=none
```

## 遇到的问题与解决方案

| # | 首个真实错误（原文） | 根因 | 修复 | 重新验证 |
|---|---|---|---|---|
| 1 | `configure: error: cannot guess build type; you must specify one` | GNU config.guess（2018-02-24）不识别 `uname -s = HarmonyOS`（知识 **E007**） | `patches/0002-config-config.guess.patch`：主 case 增加 `*:HarmonyOS:*:*)` 分支输出 `<machine>-unknown-linux-ohos`；**不使用** `--build/--host` | `./config/config.guess` → `aarch64-unknown-linux-ohos` rc=0；conan create 日志 `checking build system type... aarch64-unknown-linux-ohos` |
| 2 | 先用内置 `patch-autotools-ohos.pl`：脚本打印 `[ok] Added HarmonyOS system identification`，但 `./config/config.guess` 仍 `unable to guess system type`（rc=1） | 脚本按较新 config.guess 的 `GUESS=` 变量惯用法插入分支；本版（2018-02-24）各分支以 `echo <triplet>; exit ;;` 结束 → 插入的 arm 只赋值不输出，**静默无效** | 按本版惯用法改写为 `echo "${MACHINE}-unknown-linux-ohos"` + `exit ;;` | 同 #1 |
| 3 | `./config/config.sub aarch64-unknown-linux-ohos` → `Invalid configuration … machine 'aarch64-unknown-linux' not recognized` | config.sub（2018-02-22）`maybe_os` 与 os 合法列表均无 linux-ohos* | `patches/0003-config-config.sub.patch`（两处最小修改） | `./config/config.sub aarch64-unknown-linux-ohos` rc=0 |
| 4 | `./config.status[1066]: can't create ./confIdGoMn/subs1.awk: Permission denied` → `config.status: error: could not setup config files machinery` | HMDFS 对新建目录强制 setgid，autoconf `umask 077 && mktemp -d ./confXXXXXX` 得到属主不可写目录（知识 **E129**） | 配方 `build()` 在 configure 前 `umask 077`→`022`（generated 脚本运行时处理，不进补丁；同族 login/gssapiv2 先例） | configure rc=0，产出 config.h/config.status |
| 5 | `utils/testsuite` 运行即 `usage() + Failed with: Invalid parameter`（rc=3），且编译期告警 `result of comparison of constant -1 with expression of type 'char' is always true` | OHOS clang 下 `char` 无符号，`while ((c = getopt(...)) != EOF)` 恒真 → `switch(c)` 落 `default:` | `patches/0001-utils-testsuite.c.patch`：`char c;` → `int c;`（同族 cyrus-sasl-sql 先例） | testsuite 进入真实用例（详见下节），不再报 Invalid parameter |
| 6 | `patch -p1 < …` 报 `patching utils/testsuite.c` 且 rc=0，但文件内容未变 | 本机 CLI `patch` 是 **toybox 0.8.12**（不支持 `diff --git`/hunk 区间，静默 no-op）；Conan 用自身 `patch_ng` 实现 | 本地勘探改用字节级编辑；交付物由 `refresh-patch --auto` 生成补丁、并由 `patch_ng` 验证可应用（3/3 apply=True） | `patch_ng` 逐条 `apply=True`，且应用后文件含预期改动 |
| 7 | `refresh-patch --auto` 生成 `0004-utils-testsuite.c.patch` 达 62 KB / 2438 行 | 用 filemgr 编辑源码时**行尾空白被规范化**，产生 353 行空白噪声差异 | 从 `.orig` 重建 pristine `.work`，改用 python 字节级替换（保持行尾空白），重新生成补丁 | 生成补丁降为 **+1/-1**（0001）、**+11/-0**（0002）、**+2/-2**（0003） |
| 8 | 上游样例 `sample/client`、`sample-client`、`http_digest_client` 链接失败：`ld.lld: error: undefined symbol: getpass` | musl 已移除 `getpass(3)`，上游样例仍调用 | 测试期提供兼容 shim（`evidence/ohos-getpass-shim.c`，按 getpass 语义实现，**不改样例逻辑**，不进交付配方） | 三个样例均可构建并运行（详见 `reports/upstream-tests.md`） |
| 9 | `make -C utils smtptest` → `./smtptest.c:9:10: fatal error: 'sfio.h' file not found` | 上游 `smtptest` 依赖外部 SFIO 库（AT&T sfio），制品仓与 archives 均无该库 | 如实记录为"上游依赖外部库，无法构建"，不作通过声明 | 同左（rc=2） |

关键探测读数（configure rc=0）：

```
HAVE_OPENSSL=1  WITH_SSL_DES=1  HAVE_SHA512=1  STATIC_DIGESTMD5=1  DO_DLOPEN=0
Makefile: LIB_DES = -lcrypto        SASL_MECHS =  libdigestmd5.la
build/host = aarch64-unknown-linux-ohos
lib/staticopen.h: SPECIFIC_{SERVER,CLIENT}_PLUG_INIT( digestmd5, "DIGEST-MD5" )
libsasl2.a 含 digestmd5_client_plug_init / digestmd5_server_plug_init（静态机制表已接线）
```

## 源码修改（补丁，均由 `refresh-patch --auto` 生成）

| 补丁 | 文件 | 改动 |
|---|---|---|
| `patches/0001-utils-testsuite.c.patch` | `utils/testsuite.c` | `char c;` → `int c;`（getopt EOF 判定）。+1/-1 |
| `patches/0002-config-config.guess.patch` | `config/config.guess` | 增加 `*:HarmonyOS:*:*)` 分支输出 `aarch64-unknown-linux-ohos`。+11/-0 |
| `patches/0003-config-config.sub.patch` | `config/config.sub` | `maybe_os` 增 `linux-ohos*`；os 合法列表增 `-linux-ohos*`。+2/-2 |

三个补丁均**不含平台宏**（无 `__OHOS__`），无 stub，不涉及生成文件之外的替换；`patch_ng` 逐条应用验证通过。
（generated 脚本 `configure` 的 umask 修补不生成补丁，由配方 `build()` 运行时处理——同族 login/gssapiv2 先例。）

## 依赖版本

| 依赖 | 版本 | 类型 | 可消费性证据 |
|---|---|---|---|
| openssl | 3.5.6 | R（DES 特性门控，默认开启） | `conan download "openssl/3.5.6" -r=ohpcd --only-recipe` → rc=0；`conan download "openssl/3.5.6:*" -r=ohpcd -p "os=OHOS AND arch=armv8 AND compiler=clang"` → rc=0（package `6b129b06…`） |

## 上游测试（真实执行读数）

上游**无自动化测试目标**：`grep -rn "check_PROGRAMS\|^TESTS\|TESTS *=" Makefile.am */Makefile.am` 与 `grep -rn "check-local\|check-am\|^check:" …` 均 0 命中；无 `CMakeLists.txt`/`meson.build`/`test_*.py`/`*_test.c`；`make check` 只构建 `dbconverter-2`/`pluginviewer`，无任何测试执行。上游唯一自包含断言测试台是 `utils/testsuite.c`（`utils/Makefile.am:49 EXTRA_PROGRAMS`），已真实构建并执行：

| 指标 | 值 |
|---|---|
| discovered（`main()` 标号阶段数） | 19 |
| executed | 1（首阶段 `Checking plaintext passwords` = `test_checkpass`） |
| passed | 0 |
| failed | 1（`Failed with: sasl_checkpass() failed on simple case`） |
| skipped | 18（fatal() 直接 exit(3)，其余阶段不可达） |
| rc | 3 |
| 变体一致性 | 默认 / `-n` / `-r 3` / `-a` × 动态(`testsuite`)/静态(`testsuitestatic`) 六次实测一致 |

配方以机器证据行如实留痕（**不冒充通过**）：

```
HMBS_UPSTREAM_TEST_RESULT={"status": "blocked_by_userdb", "framework": "cyrus-utils-testsuite",
 "command": "make -C utils testsuite && SASL_PATH=<empty> ./utils/testsuite",
 "discovered": 19, "executed": 1, "passed": 0, "failed": 1, "skipped": 18, "rc": 3, "reason": "…"}
```

阻塞的**具体技术原因**：`main()` 在 `init(seed)` 之后的第二动作即 `test_checkpass()`，要求已初始化的 sasldb 口令库（上游源码顶部 NOTE 原文："Must be able to read sasldb, which needs to be setup with a username and a password"）；本包按 DIGEST-MD5 最小闭包构建（`--with-dblib=none`，configure 输出 `checking DB library to use... none` + `WARNING: Disabling SASL authentication database support`），口令库后端属独立子包。

构建期上游工具冒烟（`build()` 内断言）：`utils/pluginviewer -c`（`SASL_PATH` 置空）必须输出含 `DIGEST-MD5` **且**含 `best SSF: 128`（后者证明 DES/OpenSSL 机密性层 `WITH_SSL_DES` 生效；auth-only 机制会是 0）。

上游样例（全部真实构建并运行）：`sample/sample-server`、`sample/server` 原生构建通过；`sample/sample-client`、`sample/client`、`sample/http_digest_client` 需 musl 已移除的 `getpass` 兼容 shim（仅测试用，不进交付配方）；`sample-server` 机制列表输出 base64 `RElHRVNULU1ENQ==`（= `DIGEST-MD5`）。`utils/smtptest` 依赖外部 SFIO（`#include <sfio.h>`），制品仓/archives 均无 → 无法构建（如实记录）。`utils/saslpasswd2`/`sasldblistusers2` 构建通过，运行分别打印 usage / `check_db unsuccessful`（`--with-dblib=none` 预期）。

详细逐项日志（本地证据，`reports/` 已被 .gitignore 忽略，故关键读数已并入本节）：`reports/upstream-tests.md`、`reports/test-report.md`。

## 验证结果

| 门禁 | 结果 | 证据 |
|---|---|---|
| 真实构建（configure + make + make install） | rc=0 | `WITH_SSL_DES=1`、`HAVE_OPENSSL=1`、`STATIC_DIGESTMD5=1`、`DO_DLOPEN=0`；`LIB_DES = -lcrypto`；`SASL_MECHS = libdigestmd5.la` |
| conan create（CI 同参） | **rc=0** | `test_package` 8/8（`HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, "discovered": 8, "passedCount": 8}`） |
| test_package（消费者） | **8/8 PASS** | 其中 2 项鸿蒙特有：`ohos-static-mechanism-table-no-dlopen`（SASL_PATH 空目录下 DIGEST-MD5 仍可用 → 来自 `libsasl2.a` 静态机制表）、`ohos-openssl-des-provider`（DES 入口经包传播的链接闭包可解析） |
| conan-verify | **Verdict PASS** | G0/G1/G2/G3/G4 全 PASS（`reports/conan-verify-report.md`） |
| finish → W3 本地 CI | **通过（Pass rate 100% (1/1)）** | `L0_RESULT=pass` / `L1_RESULT=pass: upstream tests + test_package executed` / `L2_RESULT=skip: no bin/ dir` / `L4_RESULT=warn`（`gets` 子串误报，见下）/ `L5_RESULT=pass`；`.ci-result.json` `exit_code=0`（integrity_hash `8cab89996221a267`） |
| JC 杂项文件（prdiff = CI 口径） | **PASS**（Junk Files: 0；涉及软件数 1 合规） | `evidence/58a-jc.log` |
| KC 知识库 | **PASS**（Errors: 0） | `evidence/56b-kc.log` |

已知告警逐条归因（均非本包缺陷）：

1. **`G0: configure 失败 (exit 1)`**（finish Step 3，非阻塞）：G0 的干净轮以**手工 `./configure`** 复现，不走配方 `build()` 的 OHOS 运行时修补（`umask 077`→`022`，E129），故命中 `config.status: can't create ./conf*/subs1.awk: Permission denied`；配方路径下 configure rc=0（conan create 日志可证）。
2. **`L4: dangerous functions in patches`（warn）**：`gets\b` 子串误报 —— `config/config.sub` 补丁上下文含 `targets` 被该模式命中；补丁实际只增/改 `linux-ohos*` 与 `char c`→`int c`。
3. **JC full 模式（整仓扫描）命中 3 个他包已跟踪文件**（`archives/c/cloog/0.21.1/.build-closed`、`.staging-verified`、`archives/k/kics/2.1.20/.staging-verified`，`git cat-file -e origin/main:…` 确认存在于 main）：与本 PR 无关；本 PR 在 prdiff 模式下 JC 全绿。
4. **知识图谱 W5 报 1600 条草稿待审 + `E305.kv` 字段为空**：仓库既有状态，非本次新增；本次新增 2 对草稿已通过 KC。
5. **`reports/` 与 `packaging/` 等被 .gitignore 忽略**：属本地证据/收尾产物，不入 PR；关键读数已并入本 notes.md 与 `test_package/MANIFEST.yml`。

构建期真实执行（rc=0）：

```bash
$ SASL_PATH=<empty> ./utils/pluginviewer -c
Installed and properly configured SASL (client side) mechanisms are:
  DIGEST-MD5 EXTERNAL
Plugin "DIGEST-MD5" [loaded], 	API version: 4
	SASL mechanism: DIGEST-MD5, best SSF: 128
	security flags: NO_ANONYMOUS|NO_PLAINTEXT|MUTUAL_AUTH
	features: PROXY_AUTHENTICATION|NEED_SERVER_FQDN|SUPPORTS_HTTP
```

`best SSF: 128` 与 `WITH_SSL_DES=1` 共同表明 DES/OpenSSL 机密性层已编译进机制。

## 交付物

| 文件 | 说明 |
|---|---|
| `conanfile.py` | Conan 配方（autotools；静态默认；含 OHOS 运行时修补、DIGEST-MD5 特征断言、上游 harness 执行与证据留痕、pluginviewer 冒烟） |
| `conandata.yml` | 源码 URL + sha256 + 3 个补丁声明 |
| `patches/0001..0003` | 上游测试可移植性 + config.guess/config.sub 的 HarmonyOS 三元组支持 |
| `test_package/` | 消费者测试 8 项（含 2 项鸿蒙特有用例）+ MANIFEST.yml 上游测试声明 |
| `manifest.yaml` | 版本级元数据 + 补丁分类 + 知识沉淀 |
| `reports/upstream-tests.md` | 上游测试逐项执行报告 |

## 注意事项

- 服务端 DIGEST-MD5 需要用户**明文口令**（auxprop 后端：sasldb/SQL/LDAP）。本机制包按最小闭包构建（`--with-dblib=none`），不提供口令库后端；完整口令交换需与对应 auxprop 包组合使用。这也是上游 `utils/testsuite` 在本配置下首例即阻塞的原因。
- 静态包（默认）不声明 `bindirs`，`make install` 安装的 `sbin/pluginviewer` 属上游工具而非本包 CLI 契约，故不创建 `commands.json`（与同族 `cyrus-sasl-login`/`cyrus-sasl-gssapiv2` 一致）。
- 本机 CLI `patch` 为 toybox 实现（静默 no-op），本地勘探勿用其判断补丁有效性；Conan 侧 `patch_ng` 与 CI 侧 `patch` 均正常。
---

**编译结束**: 2026-09-26 09:49
**最终状态**: built
