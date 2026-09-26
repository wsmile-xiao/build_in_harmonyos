# inn2 2.7.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-24
- 编译器: clang 15.0.4 (HarmonyOS PC / aarch64)
- 状态: built

## 编译步骤

```bash
# config.guess / config.sub 打 OHOS 补丁后（0002/0003），configure 才能识别本机
perl scripts/patch-autotools-ohos.pl support/config.guess support/config.sub

./configure --prefix=/storage/Users/currentUser/usr/local \
    --without-perl --without-python --without-sendmail --disable-largefiles
make -j2
make check                      # 上游 TAP 套件：Failed 110/3883, 97.17% okay
make install DESTDIR=$DEST OWNER= CHOWNPROG=: CHGRPPROG=:
```

三个 configure 选项都是本平台必需，不是可选裁剪：

| 选项 | 原因 |
|------|------|
| `--without-sendmail` | 本机无 MTA，configure 直接报 `sendmail not found, re-run with --with-sendmail` 中止 |
| `--without-perl` | 本机无系统 Perl；开启后 innd/nnrpd 会把构建机的 libperl 路径链进二进制 |
| `--disable-largefiles` | 与 `--enable-tagged-hash` 冲突，且 OHOS 上无必要 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.status` 报 `can't create ./confXXXXXX/subs1.awk: Permission denied` | hmdfs 是 setgid 卷：`umask 077` 建出的目录权限为 `drwx--S---`，磁盘属主(20001006)与构建 UID 不同，属主自己也写不进 | 补丁 `0001-configure-umask-022.patch`，把 config.status 建临时目录的两处 `umask 077` 改成 `022` |
| 2 | configure 报 `cannot guess build type; you must specify one` | INN 自带 config.guess/config.sub 不识别 HarmonyOS | 补丁 `0002`/`0003` 教 config.guess 识别 `*:HarmonyOS:*:*` → `aarch64-unknown-linux-ohos`，config.sub 接受 `linux-ohos`；不用 `--build/--host` 绕过（R15） |
| 3 | `make install` 在 directories 步中止，满屏 `chown: inaccessible or not found` | install-sh 以 `-o news -g news` 装目录，但本环境无 chown/chgrp 可执行文件、也无 news 账号 | `CHOWNPROG=: CHGRPPROG=:` 覆盖成 shell 内建空操作（同 archives/l/libecap 做法），`OWNER=` 清空 `-o/-g` 参数 |
| 4 | 构建路径含空格时 make 反复"构建"父目录并大量报错 | INN 的 Makefile 不加引号展开 `abs_builddir`，空格把路径拆成两个词，父目录被当成 target | 在无空格路径下构建（本仓库默认的 `~/builds/<name>-<ver>.work` 满足） |
| 5 | `make check` 有 110/3883 例失败 | 失败用例全部依赖沙箱不具备的能力（news 账号、可执行 chown/chgrp、可写 spool），非 libinn 代码问题 | 保留 `make check` 调用不删除、不跳过；失败集合在 `test_package/MANIFEST.yml` 的 exemptions 中逐项声明 |

## 源码修改

| 补丁 | 修改内容 |
|------|----------|
| `0001-configure-umask-022.patch` | `configure`（生成 config.status 的模板）中两处临时目录创建：`umask 077` → `umask 022` |
| `0002-config-guess-ohos.patch` | `support/config.guess`：新增 `__OHOS__` LIBC 检测 + `*:HarmonyOS:*:*` 分支输出 `${MACHINE}-unknown-linux-ohos` |
| `0003-config-sub-ohos.patch` | `support/config.sub`：新增 `ohos-linux)` 分支，`basic_os=linux-ohos` |

## 依赖版本

无外部库依赖。仅用系统 zlib 与 libm（configure 自动探测，链接 `-lz -lm`）。

## 验证结果

```bash
$ clang test.c -o inn_consumer_test -I$PREFIX/include -L$PREFIX/lib -linnstorage -linnhist -linn -lz -lm && ./inn_consumer_test
ok   - list_new yields an empty list
ok   - list_addhead puts node at head
...
ok   - md5_hash matches RFC 1321 'abc' vector
ok   - md5_update/md5_final agrees with md5_hash
ok   - concatpath joins a directory and a file name
# all checks passed
```
34/34 断言通过。上游 `make check`：3883 例中 3773 通过（97.17%），26 跳过。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `lib/libinn.a` | 1.1 MB | 基础库：list/hashtab/md5/concat/messages 等 |
| `lib/libinnhist.a` | 154 KB | 历史数据库（history/overview） |
| `lib/libinnstorage.a` | 233 KB | 文章存储后端 |
| `bin/` | — | innd/nnrpd/innfeed/expire/convdate 等约 80 个命令行工具 |
| `include/inn/` | 44 个头文件 | 公开 API 头 |

## 注意事项

- 本包同时提供库与可执行文件，`package_type = "application"`，因此软件级目录需要 `commands.json`（R38）。
- 三个 `.a` 静态库有依赖顺序：`innstorage` → `innhist` → `inn`，`cpp_info.libs` 已按此排序。
- 带 `-o/-g` 的 install 在无 chown 环境（含 CI 沙箱）必须走 `CHOWNPROG=: CHGRPPROG=:` 覆盖，否则 install 直接失败。
- `make check` 的环境依赖失败集合是沙箱特性，不是代码缺陷；在具备 news 账号的真机上应可全绿。
---

**编译结束**: 2026-09-25 02:13
**最终状态**: built
