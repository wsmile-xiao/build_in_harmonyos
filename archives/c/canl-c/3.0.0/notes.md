# canl-c 3.0.0 适配笔记

## 编译环境
- 构建系统: makefile（EMI 自定义 Makefile + libtool）
- 编译日期: 2026-09-05
- 编译器: clang（/data/service/hnp/bin/clang，OHOS aarch64）
- 状态: built

## 编译步骤

上游为 EGEE/EMI 风格构建：顶层 Makefile 直接驱动 libtool（compile/link/install），
`perl ./src/gen_err_codes.pl` 生成 canl_err.h，`perl ./src/gen_err_desc.pl` 生成
canl_err_desc.c，bison 由 src/proxy/*_parse.y 生成 *_parse.c（lex 为预煮 .c.in，
无需 flex）。顶层 `configure` 是 Perl 脚本（生成 Makefile.inc 固化 staging 路径），
配方跳过它，全部变量经 make 命令行/环境注入：

```bash
export BISON_PKGDATADIR=<bison包>/share/bison
export CFLAGS="-O2 -I<krb5_include>"        # 环境变量注入，Makefile 以 ${CFLAGS} 追加
export LDFLAGS="-L<cares_lib> -L<openssl_lib>"
make -j1 CC=clang \
  LIBCARES_CFLAGS="-I<cares_include>" LIBSSL_CFLAGS="-I<openssl_include>" \
  LIBCARES_LIBS="-lcares" LIBSSL_LIBS="-lssl -lcrypto" all
make -j1 ... INSTALL="libtool --mode=install <单词install wrapper>" \
  install DESTDIR=<package_folder> prefix=/
```

libtool versioning：version=3.0.0、offset=1 → `-version-info 4:0:0` →
`libcanl_c.so.4.0.0`（SONAME `libcanl_c.so.4`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./src/gen_err_desc.pl: No such file or directory` | Makefile 直接执行 .pl，依赖 `#!/usr/bin/perl`；OHOS 无 /usr/bin/perl | 补丁 0001：引入 `PERL?=perl` 并以 `$(PERL)` 调用 |
| 2 | `NETDB_SUCCESS`/`NETDB_INTERNAL` 未定义 | glibc 扩展宏，musl netdb.h 无 | 补丁 0002：canl_locl.h 中 `#ifndef` 兜底（glibc 不受影响） |
| 3 | `pdflatex: inaccessible or not found` | `all`/`install` 硬依赖 doc 目标 | 补丁 0003：`BUILD_DOC?=0` 守卫，`make BUILD_DOC=1` 仍可建文档 |
| 4 | 示例工具编译报 `openssl/ssl.h` not found | CFLAGS_CLI/SER/PRX/DEL 无依赖头路径 | 补丁 0003：四变量追加 `${LIBSSL_CFLAGS} ${LIBCARES_CFLAGS}` |
| 5 | 命令行 `CFLAGS=` 覆盖导致 `-Isrc/proxy` 丢失 | Makefile `CFLAGS:=-Wall -g -I... ${CFLAGS}`，命令行变量整体覆盖 | CFLAGS 改经环境变量注入（Makefile 追加环境值） |
| 6 | bison 报 `/share/bison/m4sugar/m4sugar.m4: cannot open` | Conan bison 包数据目录不在其编译前缀 | 设 `BISON_PKGDATADIR=<pkg>/share/bison` |
| 7 | libtool 链接 `server` 报 undefined `canl_err_descs` | 前一轮失败时 shell 重定向先创建空 canl_err_desc.c，make 视为最新 | 清理陈旧生成物；配方用单一 make 流程避免半成品 |
| 8 | `libtool --mode=install` 报 "is not a directory" | libtool 要求安装程序为单个词；且 OHOS 无 `install` 命令 | 单词 wrapper（系统 install → busybox install → 纯 sh 最小实现） |
| 9 | server/client 报 "No key or certificate found" | 无 /etc/grid-security 布局时 proxy_get_filenames 在 cert_dir 兜底常量上 checkstat 失败 goto err，即使 API 已设凭证也误报 | 补丁 0004：noCertFound 判定不再受默认布局探测失败影响；运行期以 X509_CERT_DIR 提供 CA 目录（上游自有机制） |
| 10 | client 报 "Cannot validate server hostname" | 证书 CN 与连接主机不匹配 | 测试用 CN=127.0.0.1 证书（属测试正确性问题，非移植问题） |

## 源码修改

- patches/0001-makefile-perl-variable.patch：Makefile 引入 PERL 变量调用 gen_err*.pl
- patches/0002-netdb-musl-compat-macros.patch：canl_locl.h 定义 musl 缺失的 NETDB 宏
- patches/0003-makefile-optional-doc-and-dep-flags.patch：Makefile BUILD_DOC 守卫 + 示例 CFLAGS 追加依赖头
- patches/0004-ssl-nocertfound-false-positive.patch：canl_ssl.c 两处 noCertFound 判定修正

## 依赖版本

- openssl/3.0.16（静态链入 libcanl_c.so；NEEDED 仅 libc）
- c-ares/1.34.6（同上）
- krb5/1.22.1（头文件用途）
- tool_requires: libtool/2.5.4、bison/3.8.2、perl/5.42.2

## 验证结果

```bash
# 原生回环 TLS 端到端（设备实跑）
emi-canl-server -p 14327 -c cert.pem -k key.pem &
emi-canl-client -s 127.0.0.1 -p 14327 -c cert.pem -k key.pem
# client exit=0
# [CLIENT] connection established
# [CLIENT] received: This is a testing message to send
# [SERVER] received: This is the testing message to send
```

上游无自带测试套件：顶层 Makefile 的 `check:` 目标为空（无任何配方行），
ChangeLog/仓库内无测试目录。上游测试用例数为 0 属上游事实，非跳过。

## 注意事项

- Makefile 中间生成文件（*_parse.c 等）在 make 结束时会被隐式规则链清理；
  `make install` 会重新生成，无需手工干预。
- .la 文件固化构建机路径，打包时移除（lib/*.la）。
- 公开头文件 canl.h 包含 <gssapi.h>、canl_ssl.h 包含 <openssl/ssl.h>，
  消费者需 krb5 与 openssl 头文件路径（cpp_info.requires 已声明传递）。
