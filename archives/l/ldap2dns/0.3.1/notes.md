# ldap2dns 0.3.1 适配笔记

## 编译环境
- 构建系统: makefile（非 autotools，无 configure）
- 编译日期: 2026-09-20
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，target aarch64-unknown-linux-ohos）
- 状态: published
- 依赖: openldap/2.6.7（ohpcd 已发布；conan install --requires=openldap/2.6.7 -r=ohpcd 获取头文件/库）

## 编译步骤
```bash
# 1) 依赖注入（conan 制品仓拉取 openldap 预编译包）
conan install --requires=openldap/2.6.7 -r=ohpcd -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=never

# 2) 手动编译（探索阶段验证，P=<openldap package_folder>）
make CC="clang -O2" CCDEBUG="clang -g" LD="clang" \
     INC="-I$P/include -DLDAP_DEPRECATED=1" LDFLAGS="-L$P/lib"
# → 产出 ldap2dns / ldap2dnsd / ldap2dns-dbg
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ldap2dns.c:29:8: error: unknown type name 'time_t'` | 源文件用 `time_t time_now` 但未 `#include <time.h>`（glibc 下靠传递包含侥幸编译通过，musl/OHOS sysroot 不含） | 源码补 `#include <time.h>` |
| 2 | `error: call to undeclared function 'ldap_init'` / `ldap_simple_bind_s` / `ldap_search_s` | OpenLDAP 2.6 头文件把旧版 LDAP API 声明放在 `#if LDAP_DEPRECATED` 内，本包未定义该宏→声明被隐藏；符号仍在 libldap.so 导出（nm 验证） | CFLAGS 加 `-DLDAP_DEPRECATED=1` |
| 3 | `make: *** No rule to make target '-lldap'` | 上游 Makefile 把 `$(LIBS)` 写进 prerequisites（`ldap2dns: ldap2dns.o $(LIBS)`），make 把 `-lldap` 当目标文件 | Makefile 修改：库移到链接命令行 `$(LD) $(LDFLAGS) -o $@ $+ $(LIBS)` |
| 4 | `ln: cannot create hard link ... Operation not permitted` | HMDFS 不支持硬链接 | Makefile 的 `ln -f ldap2dns ldap2dnsd`（含 install 目标内）改为 `cp -f` |
| 5 | `cc: not found` | 本机无 gcc（Makefile 硬编码 `CC=gcc -O2`） | make 命令行覆盖 `CC=clang -O2` / `CCDEBUG=clang -g` / `LD=clang`（conanfile 内从 tools.build:compiler_executables 取 CC，R33） |
| 6 | 上游 `make install` 不可用 | 引用不存在的 `dns.at.conf`/`dns.oc.conf`，且 `install -o root -g root` 非 root 不可行 | conanfile package() 直接 copy 二进制到 bin/，不走 make install |

## 源码修改（R6 track-edit 已记录）
- `ldap2dns.c`：第 17 行后补 `#include <time.h>`
- `Makefile`：
  - `ldap2dns: ldap2dns.o $(LIBS)` → `ldap2dns: ldap2dns.o`，链接行追加 `$(LIBS)`
  - `ldap2dns-dbg: ldap2dns.o-dbg $(LIBS)` → `ldap2dns-dbg: ldap2dns.o-dbg`，链接行追加 `$(LIBS)`
  - `ln -f ldap2dns ldap2dnsd` → `cp -f ldap2dns ldap2dnsd`
  - `ln -f $(PREFIXDIR)/bin/ldap2dns $(PREFIXDIR)/bin/ldap2dnsd` → `cp -f`

## 依赖版本
- openldap/2.6.7（-lldap -llber，ohpcd 制品仓，conan 缓存路径 /storage/Users/currentUser/.conan2/p/openla04925142be38/p）

## 上游测试清点（R51 申报）
- **上游测试数：0（上游确无测试）**
- 清点证据（ldap2dns-0.3.1.orig 纯净上游解包后）：
  - 目录清单：`./webadmin`、`./webadmin/icons`，**无 `tests/`、`test/` 目录**（`find . -maxdepth 2 -type d`）
  - **无任何含 test/check 名字的文件**（`find . -iname "*test*" -o -iname "*check*"` 为空）
  - Makefile **无 check/test/installcheck 目标**（`grep -nE "^.*check.*:" Makefile` 无匹配）
  - 无 autotools 测试机制（无 configure.ac / Makefile.am / configure）
- 因此无上游测试可运行；仅做产物实质冒烟（见下）。

## 验证结果（二进制冒烟，本地真机执行）
```bash
$ ./ldap2dns -V
ldap2dns, version 0.3.1
  Copyright 2000 by Jacob Rief <jacob.rief@tiscover.com>
usage: ldap2dns[d] [-D binddn] [-b searchbase] [-o data|db] [-h host] [-p port] [-w password] [-L[filename]] [-u numsecs] [-v[v]] [-V]
# exit=1（上游 getopt 视 -V/-h 需要参数，属上游行为；正常启动、打印版本+usage、不崩溃）

$ ./ldap2dnsd -V   # argv[0] 判定 daemon 模式，同样打印版本+usage，不崩溃
$ ./ldap2dns -Z    # 非法选项 → "unrecognized option: Z" + 版本 + usage，exit=1，不崩溃
```
- 运行需 LD_LIBRARY_PATH 指向 openldap 的 lib 目录（libldap.so.2/liblber.so.2），conan 运行时由 VirtualRunEnv 注入。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Makefile 构建配方，requires openldap/2.6.7 |
| conandata.yml | 官方 Ubuntu 镜像源（archive.ubuntu.com）+ sha256 |
| test_package/ | R34 实质冒烟（执行 ldap2dns/ldap2dnsd -V） |
| commands.json | R38 工具声明（软件级） |
| patches/ | 由 finish refresh-patch --auto 固化源码修改 |

## 注意事项
- 二进制为 PIE ELF（`file` 显示 shared object，OHOS 平台 ET_DYN 可执行，正常）。
- `-V`/`-h` 因上游 getopt 选项串 `b:D:e:h:o:p:u:V:v::w:L::` 均要求参数，单独 `-V`/`-h` 会先打 "option requires an argument" 到 stderr 再打印版本/usage 并以 1 退出；此行为保留（未改源码语义，仅测试断言 stdout 版本行）。
- 源 URL 由 deb.debian.org 改为 archive.ubuntu.com（同一纯净上游 tarball，md5/sha256 一致），因 R39/PF7 禁止 Debian 重打包域名。
---

**编译结束**: 2026-09-21 07:30
**最终状态**: published
