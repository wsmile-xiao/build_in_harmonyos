# cyrus-sasl-crammd5 2.1.28 适配笔记

## 编译环境

- 构建系统: autotools（configure + make，in-source 构建）
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，默认目标 `aarch64-unknown-linux-ohos`）
- 状态: built（配方完成，待真机验证；验证通过前不标 published）
- 源码: https://github.com/cyrusimap/cyrus-sasl/releases/download/cyrus-sasl-2.1.28/cyrus-sasl-2.1.28.tar.gz
- 源码 SHA256: 7ccfc6abd01ed67c1a0924b353e526f1b766b21f42d4562ee635a8ebfc5bb38c
  （与 cyrus-sasl/2.1.28、2.1.28.1、cyrus-sasl-login/2.1.28 同源同值，本机实测一致）
- 本机: `uname -a` → `HarmonyOS localhost HongMeng Kernel 1.12.0 #1 SMP ... aarch64 Toybox`
- Conan: 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`

## 定位

- 本包是 Cyrus SASL 的 CRAM-MD5 机制包：同一份上游 2.1.28 源码，以 `--enable-cram`
  构建，产出静态 `libsasl2.a`（CRAM-MD5 经 `--with-staticsasl` 直接链入，消费方
  无需运行期 `SASL_PATH`/dlopen 插件搜索）。
- CRAM-MD5（`plugins/cram.c`，RFC 2195）是自包含 HMAC-MD5 挑战/应答机制：
  - `configure.ac:312-331`：CRAM-MD5 块不引用 OpenSSL（OpenSSL 探测在其后的 `:333`）；
  - `plugins/Makefile.am:95`：`libcrammd5_la_LIBADD = $(LIB_SOCKET) $(COMPAT_OBJS) $(PLUGIN_COMMON_OBJS)`
    —— 无 `-lcrypto`/DES/GSSAPI/DB/LDAP 项；
  - HMAC-MD5 原语来自源码树内 `lib/md5.c` + `lib/common.c`（`grep -rln hmac_md5 lib/ common/`）。
  因此本包零 Conan 依赖，与同族 `cyrus-sasl-login/2.1.28`（零依赖）同构。
- 闭包收敛：显式 `--disable-plain`（上游 `m4/plain.m4` 默认启用 PLAIN）、
  `--disable-anon/--disable-digest/--disable-scram/--disable-otp/--disable-srp/
  --disable-ntlm/--disable-login/--disable-passdss/--disable-gssapi/--disable-ldapdb/
  --disable-sql`，`--without-openssl --with-dblib=none --disable-auth-sasldb`，
  实测机制表为 `EXTERNAL CRAM-MD5`（EXTERNAL 为 SASL 内置）。

## 编译步骤

标准 autotools 流程（conanfile.py `_build_ohos_tree` 等价逻辑）：

```bash
umask 022 && TMPDIR=<writable-tmp> \
  CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh \
  CC_FOR_BUILD=clang CPP_FOR_BUILD="clang -E" \
  /system/bin/sh ./configure \
    --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu \
    --prefix=/ --disable-dependency-tracking --disable-sample \
    --disable-shared --enable-static --with-staticsasl \
    --disable-auth-sasldb --with-dblib=none \
    --disable-staticdlopen --disable-alwaystrue \
    --disable-anon --enable-cram \
    --disable-digest --disable-gssapi --disable-httpform --disable-krb4 \
    --disable-ldapdb --disable-login --disable-ntlm --disable-otp \
    --disable-passdss --disable-plain --disable-scram --disable-sia \
    --disable-sql --disable-srp --disable-srp-setpass \
    --without-saslauthd --without-authdaemond --without-des --without-gdbm \
    --without-ldap --without-mysql --without-openssl --without-opie \
    --without-pam --without-pgsql --without-pwcheck \
    --without-sqlite --without-sqlite3
make -j1
make install DESTDIR=<package> -j1
```

构建中另做一件 OHOS 适配（沿用 cyrus-sasl/2.1.28.1 同族做法）：

- 把 `plugins/cram.c` 拷到 `lib/`（`lib/Makefile.am` 的 `linksrcs` 用
  `ln -s $(SASL_STATIC_SRCS) .` 建软链；预拷贝可保证 HMDFS 拒绝软链时静态对象仍可编译），
  db_none 配置下同时把 `sasldb/db_none.c` 拷到 `lib/`；
- `config/install-sh` 拷贝到可写 tmp，重写 shebang 为 `#!/system/bin/sh` 后
  经 make 变量 `MKDIR_P`/`INSTALL*` 以单一程序路径调用
  （libtool `--mode=install` 会把 `/system/bin/sh <script>` 前缀误解析为待安装文件）。

## 遇到的问题与解决方案

| # | 问题（首个真实错误） | 根因 | 解决方案 |
|---|----------------------|------|----------|
| 1 | `./config.status[1065]: can't create ./confjcBnFC/subs1.awk: Permission denied` / `config.status: error: could not setup config files machinery` | Autoconf 生成的 `configure` 用 `umask 077` 建 `./confXXXXXX` 临时目录，HMDFS（setgid）下该目录属主不可写，`config.status` 随后写入失败 | `patches/0001-configure-ohos-umask.patch` 把 `configure:22266/22271` 的 `umask 077` 改为 `umask 022`（同 cyrus-sasl/2.1.28.1 的 0001 补丁；补丁作用于发布包内 configure，不使用运行期改写生成文件的 sed，R6） |
| 2 | `C preprocessor "/data/service/hnp/bin/clang -E" fails sanity check`，`config.log` 内为 `configure: can't fork - try again` | **平台瞬时资源耗尽**（同机并行任务过多，OS fork 失败），非配方缺陷 | 无需改配方；待资源恢复后重跑同一命令（见 reports/test-report.md「瞬时故障复现与重跑」） |
| 3 | 消费者测试首轮 `CRAM-MD5 digest mismatch`（本地重算摘要与机制输出不一致） | test_package 在 `sasl_dispose()` 之后才用服务端返回的挑战指针（该指针归 server context 所有，已被释放） | 在 dispose 前把挑战拷入私有缓冲区，再做 HMAC-MD5 比对 |
| 4 | `make install` 报 `install-sh: no input file specified` | `INSTALL="/system/bin/sh <tmp>/install-sh -c"` 带 shell 前缀，libtool `--mode=install` 把脚本路径当成待安装文件 | install-sh 拷贝后重写首行为 `#!/system/bin/sh`，`INSTALL/MKDIR_P` 改为单一程序路径（同 cyrus-sasl-login 先例） |

## 上游测试（实际执行）

- 上游 2.1.28 **无 automake `make check` 目标**（`grep -n '^TESTS\|check-local\|check-am' Makefile.am */Makefile.am` 无命中），
  但**有真实自动化测试程序**：`utils/testsuite.c`（`utils/Makefile.am:49` 以 `EXTRA_PROGRAMS` 声明），
  运行入口 `utils/testsuite -a`。
- 该测试的「Checking plaintext passwords」/「Testing auxprop functions」阶段需要 sasldb 口令库，
  故通过默认关闭的 `with_upstream_tests` + `with_sasldb` 选项：
  - 重新解包一份**临时测试树** `upstream-tests/`（避免污染交付树）；
  - 该树以 `--enable-auth-sasldb --with-dblib=lmdb` 配置并构建；
  - `lmdb/0.9.35` 为 `visible=False`、`transitive_headers/libs=True` 的目标侧依赖，
    且已在 `package_id()` 中删除（不改变交付包 ID / 不进入交付包）；
  - 用上游 `saslpasswd2 -p -f utils/sasldb -c ken`（口令 1234，`utils/testsuite.c` 内硬编码的
    凭据）建立口令 fixture，然后执行 `utils/.libs/testsuite -a`。
- 交付包本身始终来自 `db_none` 主树，不含 sasldb/LMDB。

## 源码修改

上游**产品源码**零修改。仅 2 个补丁，均属平台适配且不影响被测逻辑：

| 补丁 | 目标文件 | 性质 |
|---|---|---|
| `patches/0001-configure-ohos-umask.patch` | `configure`（Autoconf 构建脚本） | HMDFS umask 适配（见上表 #1） |
| `patches/0002-testsuite-use-int-for-getopt.patch` | `utils/testsuite.c`（**上游测试源码**） | `char c;` → `int c;`（getopt 返回值类型）。**不改变测试输入、断言与判定标准**，仅让测试程序在 OHOS aarch64 上能正常解析 `-a` 参数（否则截断 EOF 哨兵 → `Failed with: Invalid parameter`，见 attempt4）。同族 `cyrus-sasl/2.1.28.1` 的 `0003-testsuite-use-int-for-getopt.patch` 为同一改动 |

> 另有一处**运行参数**层面的固定（非源码修改）：`utils/testsuite` 用 `time(NULL)` 播种、
> corruption 阶段以 `rand()` 选取破坏字节，故 `build()` 以该程序自带的 `-s 1` 固定种子，
> 使结果可复现（未改任何测试内容）。10 种子矩阵见 `reports/upstream-testsuite-seed-matrix.txt`。

## 依赖版本

- 交付包：无外部依赖（自包含；`system_libs` 仅 `pthread`）。
- 测试闭包（默认关闭）：`lmdb/0.9.35`（visible=False，仅用于临时上游测试树的 sasldb 后端）。

## 验证结果

见 `reports/test-report.md`（上游测试逐项统计）与 `reports/conan-verify-report.md`。

## 交付物

`lib/libsasl2.a` + `include/sasl/*.h` + `lib/pkgconfig/libsasl2.pc`。

## 注意事项

- 本包与 `cyrus-sasl` 同源但包名/用途不同：`cyrus-sasl` 覆盖完整机制集（含 openssl/lmdb/sqlite3 依赖），
  本包是 CRAM-MD5 专用最小闭包（零依赖、静态、无守护进程）。
- 静态库 + `--with-staticsasl`：消费方无需设置 `SASL_PATH`，CRAM-MD5 无运行期插件加载。
- CRAM-MD5 使用 HMAC-MD5（非抗碰撞），仅用于兼容需要它的既有协议场景。
---

**编译结束**: 2026-09-26 09:04
**最终状态**: built
