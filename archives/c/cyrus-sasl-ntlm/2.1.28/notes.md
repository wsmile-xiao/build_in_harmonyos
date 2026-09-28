# cyrus-sasl-ntlm 2.1.28 适配笔记

## 编译环境

- 构建系统: autotools（configure + make，in-source 构建）
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos，/data/service/hnp/bin/clang）
- 状态: built
- 源码: https://github.com/cyrusimap/cyrus-sasl/releases/download/cyrus-sasl-2.1.28/cyrus-sasl-2.1.28.tar.gz
- 源码 SHA256: 7ccfc6abd01ed67c1a0924b353e526f1b766b21f42d4562ee635a8ebfc5bb38c（与 cyrus-sasl/2.1.28*、cyrus-sasl-login/2.1.28 同源同值）

## 定位

- 本包是 Cyrus SASL 的 NTLM 机制包：同一份上游 2.1.28 源码，以 `--enable-ntlm`
  构建，产出静态 `libsasl2.a`（NTLM 经 `STATIC_NTLM` 直接链入，消费方无需
  运行期 `SASL_PATH`/dlopen 插件搜索）。
- 与族内 LOGIN/PLAIN/ANONYMOUS 不同，NTLM 依赖密码学原语（MD4 / HMAC-MD5 /
  DES），因此本包以 `openssl/3.5.6`（静态 libcrypto）为唯一 Conan 依赖。

## 编译步骤

标准 autotools 流程：

```bash
TMPDIR=<writable-tmp> CC_FOR_BUILD=clang CPP_FOR_BUILD="clang -E" \
  ./configure --prefix=/ --disable-dependency-tracking --disable-sample \
    --disable-shared --enable-static --with-staticsasl --disable-staticdlopen \
    --disable-alwaystrue --disable-anon --disable-cram --disable-digest \
    --disable-gssapi --disable-httpform --disable-krb4 --disable-ldapdb \
    --disable-login --disable-otp --disable-passdss --disable-sia \
    --disable-sql --disable-srp --disable-srp-setpass \
    --enable-ntlm --with-openssl=<openssl pkg root> \
    --without-saslauthd --without-authdaemond --without-des --without-gdbm \
    --without-ldap --without-mysql --without-opie --without-pam \
    --without-pgsql --without-pwcheck --without-sqlite --without-sqlite3 \
    --disable-auth-sasldb --with-dblib=none
cp plugins/ntlm.c lib/ntlm.c && cp sasldb/db_none.c lib/db_none.c   # linksrcs 等效
make -j1
make install DESTDIR=<package> -j1
```

`-lcrypto` 经 conan 的 `AutotoolsDeps` 以 `LIBS` 注入（openssl/3.5.6 只有静态
归档，无运行期搜索路径需求）；`CPPFLAGS/LDFLAGS` 同时带上 openssl 的
include/lib 路径。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `cannot guess build type; you must specify one` | 上游 config.guess(2018-02-24) 的 case 表不含平台上报的 `HarmonyOS` uname | 补丁 0001/0002：config.guess 增加 `*:HarmonyOS:*:*` 分支输出 `aarch64-unknown-linux-ohos`，config.sub 接纳 `linux-ohos`/`-linux-ohos`（平台探测改动，不使用 `--build/--host`） |
| 2 | 生成配置脚本时报 `cannot create ./confXXXXXX/subs1.awk`，Permission denied | HMDFS 下 autoconf 以 `umask 077` 建临时目录，属主不可写 | 补丁 0003：生成的 configure 中 2 处 `umask 077` → `umask 022` |
| 3 | `checking whether the C compiler works... no` + configure rc=77 | `--with-openssl` 注入的 `-L` 晚于编译器可用性探测，早期 conftest 带 `-lcrypto` 却无搜索路径 | 把 openssl 的 `-L<dir>/lib` 放进 `LDFLAGS`（AutotoolsDeps 同时给出 LDFLAGS/LIBS） |
| 4 | `ld.lld: undefined symbol: HMAC_CTX_new`（dbconverter-2/pluginviewer/testsuite） | 上游 `NTLM_LIBS=-lcrypto` 只进 `plugins/libntlm.la` 的 LIBADD；`libsasl2.a` 内 `ntlm.o` 的 HMAC/MD4/DES 未定义符号需由最终链接方的 `$(LIBS)` 解析 | 由 `LIBS=-lcrypto` 提供（configure 命令行注入，automake 链接行末位） |
| 5 | `make[1]: *** No rule to make target 'ntlm.o'` / linksrcs 软链不可用 | `lib/Makefile` 的 linksrcs 目标用 `ln -s` 把 `plugins/ntlm.c`、`sasldb/db_none.c` 链入 `lib/`；HMDFS 不服务这些软链接 | 配方 `build()` 在 make 前直接拷贝这两个源到 `lib/` |
| 6 | `utils/testsuite` 报 `Invalid parameter` 直接退出 | 上游 `testsuite.c` 用 `char c` 接收 `getopt()`，aarch64 上 char 为无符号，`!= EOF` 判定失效 | 补丁 0004：改为 `int c`（仅影响可选手动测试程序） |
| 7 | `make` 尝试重跑 aclocal/automake（OHOS 无 automake） | tarball 内生成的 autotools 文件 mtime 不一致 | 归一化源码树 mtime（同 cyrus-sasl/2.1.28.3 做法） |
| 8 | 上游无自动化测试套件 | 顶层无 `make check` 目标，utils 仅 EXTRA_PROGRAMS | 按 no_tests 口径申报（MANIFEST.yml 完整审计） |
| 9 | 包内 `bin/pluginviewer` 无法运行：`Error loading shared library libsasl2.so.3`（rc=127，真机实测） | 静态包已在 `package()` 清除全部 `.so`，而该可执行文件带 `DT_NEEDED libsasl2.so.3`（RUNPATH `//lib`），加载器找不到依赖 | `package()` 删除 `bin/`、`sbin/`，交付为**纯库包**（纯库无需 `commands.json`，R38；与同族 `cyrus-sasl/2.1.28.3` 做法一致） |

## 源码修改

补丁 0001~0003 为平台适配（三元组识别、临时目录权限），补丁 0004 为可选手动
测试程序的可移植性修复；库本体源码零修改。

## 依赖版本

- openssl/3.5.6（静态 libcrypto/libssl；本包只用 libcrypto）
- system_libs: dl、resolv、pthread

## 上游测试

上游 2.1.28 **不含自动化测试套件**：顶层 Makefile.am 无 check 目标，
`utils/Makefile.am` 只有 `EXTRA_PROGRAMS`（testsuite/testsuitestatic/smtptest），
BLFS 亦记录 "This package does not come with a test suite"。

手动入口 `utils/testsuite` 实测（本次真实执行，见 MANIFEST.yml `manual_run_evidence`）：

- 前置：`printf '1234\n' | ./utils/saslpasswd2 -p -c -f ./sasldb ken` 预置口令库
- 命令：`SASL_PATH=<empty> ./testsuite -a -s 1`
- 结果：前 7 个阶段通过（checkpass / random / base64 / auxprop / init / listmech / serverstart），
  第 8 阶段 client-first 的 NTLM 子步骤崩溃；调用栈经符号化定位为
  `mdb_cursor_set`(lmdb) ← `mdb_get` ← `_sasldb_getdata` ← `sasldb_auxprop_lookup`
  ← `_sasl_auxprop_lookup` ← `_sasl_canon_user_lookup` ← `ntlm_server_mech_step`，
  即**依赖 lmdb/0.9.35 内部**（该测试闭包树为满足 testsuite 对 sasldb 的要求而启用
  `--enable-auth-sasldb --with-dblib=lmdb`）。交付配方为 `--with-dblib=none`，不含该后端。

## 验证结果

见 `reports/`：conan create / conan-verify / finish(W2+W3) 的原始日志与结论。

## 交付物

`lib/libsasl2.a` + `lib/sasl2/*.a`（静态插件归档）+ `include/sasl/*.h` +
`lib/pkgconfig/libsasl2.pc` + `share/man/` + `licenses/`。

`package()` 已移除 `bin/`、`sbin/`（见问题 #9）、全部 `*.la` 与共享库残留 —— 交付物为**纯库包**。

## 注意事项

- 本包与 `cyrus-sasl` 同源但用途不同：`cyrus-sasl` 是完整机制集（`--disable-ntlm`），
  本包是 NTLM 专用最小闭包（openssl 依赖、静态、无守护进程），供只需要 NTLM 的消费方选用。
- 静态库 + `--with-staticsasl`：消费方无需设置 `SASL_PATH`，NTLM 无运行期插件加载
  （对应 test_package 的鸿蒙特有断言 `ohos-static-mech-table`）。
- NTLM 本身是遗留协议（仅用于兼容老 SMB/Exchange 场景），安全性弱于 GSSAPI/SCRAM。
- 本轮未提交、未推送，待用户确认后再执行远端写操作。

## 对话记录

### 对话 #1 — 2026-09-26

- 任务: 适配 `cyrus-sasl-ntlm/2.1.28` 到 HarmonyOS PC（aarch64），要求真实构建、上游测试、
  test_package、conan create、conan-verify、finish、W2/W3 与 PR 文件原子性检查；停止在远端写操作之前。
- 关键结论:
  1. 上游 2.1.28 **无自动化测试套件**（顶层无 check 目标，utils 仅 EXTRA_PROGRAMS）；
     手动入口 `utils/testsuite` 需预置 sasldb，实测前 7 阶段通过后在依赖 `lmdb/0.9.35`
     的 `mdb_cursor_set` 内崩溃（调用栈已符号化），与交付配方（`--with-dblib=none`）无关。
  2. 平台适配 4 处：config.guess/config.sub 三元组识别、configure umask、可选测试程序 getopt 类型；
     构建侧另有 HMDFS `linksrcs` 软链接改用拷贝、TMPDIR 重定向、`CC_FOR_BUILD=clang`。
  3. 链接闭包: `libsasl2.a` 内 `ntlm.o` 的 HMAC/MD4/DES 未定义符号需由 `LIBS=-lcrypto` 解析
     （上游 `NTLM_LIBS` 只覆盖共享模块 `plugins/libntlm.la`）。
- 门禁: conan create rc=0；conan-verify G1–G4 PASS；finish W3 本地 CI PASS；
  test_package 7/7（含 1 项鸿蒙特有断言 `ohos-static-mech-table`）。
- 未执行: commit / push / PR / 制品上传 / 远端 Review（等待用户确认）。
---

**编译结束**: 2026-09-26 12:23
**最终状态**: built
