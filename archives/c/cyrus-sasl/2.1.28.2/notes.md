# cyrus-sasl 2.1.28.2 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
- 产出动态 `libsasl2.so.3`（SONAME `libsasl2.so.3`）+ 11 个机制/auxprop 插件（`lib/sasl2/*.so`），供 dlopen 及作依赖。
- **禁 GSSAPI/LDAPDB**（避 krb5↔openldap↔sasl 循环依赖，且 krb5/openldap 尚未进 ohpcd 制品仓）。

## 依赖（ohpcd 制品仓）
- `openssl/3.5.6`：DIGEST-MD5/CRAM-MD5/SCRAM/OTP/NTLM/SRP 密码学（静态 libcrypto.a 焊进各插件）
- `lmdb/0.9.35`：sasldb auxprop 后端（`--with-dblib=lmdb`）
- `sqlite3/3.49.1`：SQL auxprop 插件（`--enable-sql --with-sqlite3`）

## 关键适配（真机 conan create 迭代出的 delta）
1. **`CC_FOR_BUILD=clang`**：cyrus-sasl configure 用 `AC_PROG_CC_FOR_BUILD` 探 build 机编译器，
   清 host 前缀后裸搜 `gcc/cc/cl.exe`，OHOS 只有 clang → `no acceptable C compiler found`。
   本机构建 build==host，显式喂 `CC_FOR_BUILD=clang`（+`CPP_FOR_BUILD=clang -E`）。
2. **`--without-mysql --without-pgsql`**：`--enable-sql` 默认给 libsql 挂 `-lmysqlclient -lpq`，
   OHOS 无这两个库 → ld.lld unable to find library。只保留 sqlite3 后端。
3. **`--disable-sample`**：`sample/client.c` 调 `getpass()`，musl **无此符号**（已废弃移除）→
   `undefined symbol: getpass`。示例非库本体，不编。
4. **`--without-saslauthd`**：saslauthd 是服务端守护（需 PAM/shadow，OHOS 无），非库本体，不编。
5. **`-Wno-error=implicit-function-declaration -Wno-error=int-conversion`**：老代码在 clang15 下
   多处 C99 隐式声明被默认升为 error，降回 warning（发行版编老代码通用做法）。
6. **lmdb 无 `--with-lmdb`**：靠 `AutotoolsDeps` 注入 -I/-L 让 `AC_CHECK_LIB(lmdb)` 命中（同 krb5）。
7. **TMPDIR → build 目录**：HMDFS 默认 tmp 不可写，configure conftest 会 Permission denied。
8. **uname shim + umask 077→022**：autotools 通用 OHOS 适配。

## 验证结论（真机 3QC0124C20000682，2026-08-08）
- **conan create rc=0，test_package PASS**。
- 客户端 `sasl_listmech` 枚举 **14 个机制**：SRP / SCRAM-SHA-512/384/256/224/1 / DIGEST-MD5 /
  EXTERNAL / OTP / CRAM-MD5 / NTLM / PLAIN / LOGIN / ANONYMOUS。
- **11 插件 + 核心库全部 `.codesign` 已签名**；dlopen 全通。
- **DT_NEEDED 仅 `libc.so`**：openssl/lmdb/sqlite3 静态焊入 → 插件自包含、运行期零外部 .so 依赖
  （代价：libcrypto 在 5 个 crypto 插件各存一份，crypto 插件 ~4.6MB）。
- 导出 **56 个 `sasl_*` 公开函数**（上游完整 API 超集，无截断）；SONAME `libsasl2.so.3`。

## 状态
built + verified（真机 conan create + 14 机制 listmech + 符号/签名核查全过）。
尚未 upload 到 ohpcd 制品仓（待凭据 + 用户确认）。
