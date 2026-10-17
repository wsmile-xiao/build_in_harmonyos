# pen 0.34.1 HarmonyOS PC 适配笔记

## 概述

- 软件：pen 0.34.1（tcp/udp 四层负载均衡器，纯 C，autotools 构建）
- 上游：https://siag.nu/pen/ （作者 Ulric Eriksson；发布目录 https://siag.nu/pub/pen/）
- 适配路径：`archives/p/pen/0.34.1/`
- 构建目标：aarch64-linux-ohos（HarmonyOS PC / OpenHarmony，clang 15，libc++）
- 交付形态：`package_type=application`，产物 5 个可执行文件，无库
- 补丁：**0 个**（`patches/` 未创建）
- 状态：`published`（conan create + test_package 全绿）

## 决策对话记录

### 对话 #1 [2026-09-28]

- 问题: `conan create` 在 `source()` 阶段失败 `Transfer interrupted before complete: 686080 < 184622`，官方源 siag.nu 反复重试无效
- 操作: 抓响应头定位为托管代理返回 `Content-Encoding: x-gzip`（`Content-Length` 是压缩件尺寸、实际下发解压后的 tar 流），而 `conan/internal/rest/file_downloader.py` 只把字面量 `"gzip"` 当可容忍编码；改为 `conandata.yml` 使用 **url 列表**，补 OpenBSD ports distfile 与 NetBSD pkgsrc distfile 两个权威镜像
- 结果: 三源 sha256 逐字节一致；conan 自动回退并成功（`Trying another mirror.` → `Sources correctly downloaded from https://ftp.openbsd.org/pub/OpenBSD/distfiles/...`）。CI 的 curl 预下载取 1 号官方源本就正常，不受影响

### 对话 #2 [2026-09-28]

- 问题: 发布包自带预生成 `configure` 却不含 `config.guess`/`config.sub`，普通 `./configure` 无法确定 build 三元组
- 操作: 不改上游、不加补丁，改为在 configure 参数里显式给 `--build=aarch64-linux-ohos`（conan 同时下发 `--host`）
- 结果: `_AC_CANONICAL` 不再调用猜测脚本，**零补丁**通过（与 `archives/n/ngircd/28` 同法）

### 对话 #3 [2026-09-28]

- 问题: 默认构建会带 `-DDEBUGGING`（上游对 `enable_debugging` 的判定是 `test "$enable_debugging" != "no"`，即不显式关闭就默认开），运行期会向 stderr/syslog 刷每次请求的调试转储；同时若只用 `AutotoolsToolchain`，configure 探不到 OpenSSL（`HAVE_LIBSSL` 不成立、`ssl.c` 退化为空翻译单元）
- 操作: 显式 `--disable-debugging`；并在 `generate()` 中追加 `AutotoolsDeps(self).generate()` 让 openssl 的 `-I/-L` 进入 `CPPFLAGS/LDFLAGS/LIBS`
- 结果: configure 实测 `checking for main in -lcrypto... yes` / `-lssl... yes` / `EC_KEY_new_by_curve_name... yes`；`pen` 静态链入 OpenSSL，产物 `DT_NEEDED` 仅 `libc.so`

### 对话 #4 [2026-09-28]

- 问题: 上游测试入口核验——tarball 无 `tests/` 目录，`Makefile.am`/`configure.ac` 未注册 `TESTS`/`check_PROGRAMS`，需确认 `make check` 究竟是"没测试"还是"测试失败"
- 操作: 在 OHOS 构建树内真实执行 `make check` 并核对 `Makefile.in` 定义；同时在 `conanfile.py` 的 `build()` 内调用 `make check` 让 CI 日志留痕
- 结果: `make check` 退出 0 且无任何输出——`check` = `check-am` = `all-am` 是空目标，**上游确无自动化测试**（清点证据 `reports/upstream-test-inventory.log`，实测证据 `reports/upstream-test-run.log`）

### 对话 #5 [2026-09-28]

- 问题: 上游无测试，需按"至少新增一个鸿蒙消费者用例且不能是断言"补足；同时 `penlogd` 转发后立刻读日志恒为 0 字节，易被误判为转发失败
- 操作: 用 pen 自带的 `penlog`/`penlogd`（UDP）与 `penctl`（TCP 控制面）互相驱动，构造 4 条真实数据往返用例（无任何 `assert`）；排查后确认是上游 `fopen(...,"a")` + stdio 缓冲，需进程 `fclose` 才落盘，故用例改为先 `kill -TERM` 触发 SIGTERM handler→优雅退出→`fclose` 再读日志
- 结果: `conan create` 内 4/4 PASS（`cases=4 failed=0`，见 `reports/ohos-consumer-test.log`）；W3 本地 CI 模拟 1/1 (100%) PASS，L1e 反向验证（移走 `bin/` 后用例必须失败）确认用例真实依赖被测产物

### 对话 #6 [2026-09-28 — PR #13561 首轮 CI 失败修复]

- 问题: PR #13561 首轮远程 CI（构建 #63784）失败：`./config.status: line 615: ./confakipJO/subs1.awk: Permission denied` → `could not setup config files machinery`。CI 机器人把类别误判为"网络问题/源码下载超时"，但日志显示源码实际已从 OpenBSD 镜像成功下载——真实根因是 **worker 的 conan 缓存在 HMDFS**（`/storage/Users/currentUser/.cache/conan2`），autoconf 2.69 的 `config.status` 用 `umask 077 && mktemp -d "./confXXXXXX"` 创建 0700 临时目录后，进程因 HMDFS 的 UID 映射无法写回自己刚建的目录。本地构建不触发是因为本地 CONAN_HOME 在 el2 层（ext4 语义正常）
- 操作: 在 `conanfile.py` 的 `build()` 内、`autotools.configure()` 之前内联替换 `configure` 里的 tmp 目录块（`mktemp -d` → 普通 `mkdir`，默认 umask 0755）。该文本位于 quoted heredoc 内，**改 configure 一处即同时修复 configure 自身与它生成的 config.status**（实测 configure:5833 → config.status:586）。修法与已合并先例 `archives/4/4ti2/1.6.10` 完全一致；比 `umask 077→007` 可靠——mktemp 强制 0700，umask 只能收紧不能放宽
- 结果: 隔离 CONAN_HOME 完整重跑 `conan create`：补丁命中日志 `OHOS fix: configure mktemp->mkdir patch applied`、包 ID 不变（`bb90e580ad95…`）、消费者用例 4/4 PASS；产物 `config.status` 实测 586-588 行已是 `mkdir` 形态，残留的 592 行 `umask 077` 是永远走不到的死回退分支（第一分支成功后 `||` 短路）。**零源码补丁属性不变**（内联替换发生在构建树，`patches/` 仍为空）

## 依赖决策（W0 / R36）

| 探测项 | 上游 configure 行为 | 决策 | 依据 |
|---|---|---|---|
| `openssl`（`--with-ssl`） | 默认开：`AC_CHECK_LIB(crypto, main)` + `AC_CHECK_LIB(ssl, main)` | **启用** | `openssl/3.5.8.1` 已发布到 ohpcd，`conan download openssl/3.5.8.1 -r=ohpcd -p "os=OHOS AND arch=armv8"` 成功（静态包，`shared: False`）。TLS 前端/后端是 pen 核心功能之一，保留 |
| `libGeoIP`（`--with-geoip`） | 默认开：`AC_CHECK_LIB([GeoIP],[GeoIP_country_code_by_addr])` | **`--without-geoip`** | 制品仓无 libgeoip；GeoIP 仅影响统计页的国家字段 |
| netmap DSR（`--with-dsr`） | 默认开：`AC_CHECK_HEADERS([linux/if_packet.h])` + `AC_CHECK_HEADERS([net/netmap_user.h])` | **`--without-dsr`** | DSR 依赖 netmap 用户态头，OHOS 无对应实现；不影响普通代理模式 |
| `-lsocket` / `-lnsl` / `-lresolv` | `AC_CHECK_LIB` 探测 | 不改 | OHOS 上 `-lsocket`/`-lnsl` 未命中（正常），`-lresolv` 命中但不产生 `DT_NEEDED`（musl 内建解析器），无需处理 |

`conan download` 实测证据（本机、隔离 CONAN_HOME）：

```
$ conan download openssl/3.5.8.1 -r=ohpcd --only-recipe      → exit 0
Downloading recipe 'openssl/3.5.8.1#0825772c02c4be90c6add143a1fadadc'
$ conan download openssl/3.5.8.1 -r=ohpcd -p "os=OHOS AND arch=armv8"   → exit 0
openssl/3.5.8.1: Package installed 4b977264131a1c74e82bd6bb51b63cc9aadc4cfa
openssl/3.5.8.1: Downloaded package revision 773b7a4d178a42435ebf441e26dbd416
```

全部构建在隔离 `CONAN_HOME`（`conan-home-pen`）下执行，依赖只会从 ohpcd 现取，不复用主缓存
里的既有二进制；构建命令使用 `--build='pen/*'`（**未使用 `--build=missing`**），依赖若缺失会
直接报 missing binary，而不是回退源码编译。

## 编译步骤（实测命令）

```
configure --prefix=/ --bindir=${prefix}/bin --sbindir=${prefix}/bin --libdir=${prefix}/lib \
  --includedir=${prefix}/include --oldincludedir=${prefix}/include \
  --with-ssl --without-geoip --without-dsr --disable-debugging --build=aarch64-linux-ohos
make -j20
make check        # 上游测试入口，见下
make install
```

关键点：

1. **`--build=aarch64-linux-ohos` 必需**：发布包自带 `configure`（autoconf 2.69）与
   `Makefile.in`，但**不带 `config.guess`/`config.sub`**（tarball 内 74 个文件逐一核对无此二文件）。
   显式给出三元组即可让 `_AC_CANONICAL` 不再调用猜测脚本，零补丁通过。
2. **`--disable-debugging` 必需**：上游对 `enable_debugging` 的判定是
   `test "$enable_debugging" != "no"`，即**未显式关闭时默认打开 `-DDEBUGGING`**，
   发布包会往 stderr/syslog 打每次请求的调试转储。
3. **OpenSSL 可见性靠 AutotoolsDeps**：Conan 2.29 的 `AutotoolsToolchain` 不下发依赖
   `-I/-L`；`AutotoolsDeps(self).generate()` 才把 openssl 的 include/lib 送进
   `CPPFLAGS/LDFLAGS/LIBS`。实测 configure 输出
   `checking for main in -lcrypto... yes` / `checking for main in -lssl... yes` /
   `checking for EC_KEY_new_by_curve_name... yes`，`config.h` 中 `HAVE_LIBSSL` 生效。
4. **`AC_CHECK_LIB(lib, main)` 的语义**：conftest 生成的是
   `int main(){ return main(); }`（自递归），因此它实际只验证"该库能否链接"，
   静态 `libssl.a`/`libcrypto.a` 同样命中——不必为静态 OpenSSL 打补丁。
5. 链接行（实测）：`-lssl -lcrypto -lresolv -lssl -lcrypto -ldl -lpthread`，
   但产物 `DT_NEEDED` 只有 `libc.so`（OpenSSL 静态链入）。
6. 事件后端自动探测命中 `epoll_create1` 与 `poll`（`HAVE_EPOLL`/`HAVE_POLL`），
   `kqueue` 未命中属预期（非 BSD）。

### 编译告警（上游自身代码，非适配引入，按最小改动原则不修）

全量 **9 条**，逐条取自 `reports/w3-local-ci.log`（`grep -c 'warning:' = 9`）：

| # | 位置 | 告警 | 类别 |
|---|---|---|---|
| 1 | `pen.c:157:6` | `unused variable 'n'` | `-Wunused-variable` |
| 2 | `ssl.c:81:14` | `'RSA_new' is deprecated` | OpenSSL 3.0 弃用 |
| 3 | `ssl.c:86:8` | `'RSA_generate_key_ex' is deprecated` | OpenSSL 3.0 弃用 |
| 4 | `ssl.c:88:4` | `'RSA_free' is deprecated` | OpenSSL 3.0 弃用 |
| 5 | `ssl.c:99:14` | `unused variable 'state'` | `-Wunused-variable` |
| 6 | `ssl.c:100:14` | `unused variable 'type'` | `-Wunused-variable` |
| 7 | `ssl.c:101:14` | `unused variable 'desc'` | `-Wunused-variable` |
| 8 | `ssl.c:387:17` | `'EC_KEY_new_by_curve_name' is deprecated` | OpenSSL 3.0 弃用 |
| 9 | `ssl.c:396:3` | `'EC_KEY_free' is deprecated` | OpenSSL 3.0 弃用 |

**结论**：9 条（`pen.c` 1 条 + `ssl.c` 8 条）全部来自上游源码，**零补丁、无适配引入告警**。
第 5/6/7 条（`ssl.c` 的 `state`/`type`/`desc`）是 `--disable-debugging` 关闭 `DEBUGGING`
宏后这些变量失去使用点才暴露，属上游代码在 release 配置下的固有形态，同样不是适配引入。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `conan create` 在 `source()` 阶段失败：`Transfer interrupted before complete: 686080 < 184622` | 官方站 siag.nu 由 Loopia 托管代理返回 `Content-Encoding: x-gzip`，且 `Content-Length` 是压缩件尺寸、实际下发解压后的 tar 流；Conan 的 `file_downloader.py` 只把字面量 `"gzip"` 当作可容忍编码，尺寸比对处直接抛错 | `conandata.yml` 用 **url 列表**：官方源 + OpenBSD ports distfile + NetBSD pkgsrc distfile（三者 sha256 逐字节一致）。本地会自动落到 2 号源；CI 的 curl 预下载本就取 1 号源成功 |
| 2 | 若不带 `--build=`，configure 报无法猜测 build 三元组（发布包缺 config.guess/config.sub） | 上游 tarball 未随包分发 autoconf 辅助脚本 | 显式 `--build=aarch64-linux-ohos` 跳过猜测 |
| 3 | 默认构建带 `-DDEBUGGING`，运行期刷调试日志 | 上游 `--enable-debugging` 默认开 | 显式 `--disable-debugging` |
| 4 | 若只用 AutotoolsToolchain，configure 探不到 OpenSSL，`ssl.c` 退化为空单元且链接缺符号 | Conan 2.29 不下发依赖 `-I/-L` | 追加 `AutotoolsDeps(self).generate()` |
| 5 | PR #13561 首轮远程 CI 失败：`config.status: ./confXXXXXX/subs1.awk: Permission denied`（worker conan 缓存在 HMDFS，`mktemp -d` 0700 目录无法写回） | HMDFS UID 映射 + autoconf 2.69 的 `umask 077 && mktemp -d "./confXXXXXX"`；本地 el2 缓存不触发，属 CI-worker 特有路径 | `build()` 内内联替换 configure 的 tmp 目录块：`mktemp -d` → 普通 `mkdir`（默认 umask）；heredoc 传导使 config.status 同时修复（先例 `archives/4/4ti2/1.6.10`） |

## 源码修改

无。`patches/` 目录不存在，`conandata.yml` 无 `patches:` 段。

构建树内联替换（不属源码补丁，`patches/` 仍为空）：`build()` 在 configure 前把
`configure` 文本里的 `umask 077 && mktemp -d "./confXXXXXX"` 替换为普通 `mkdir`
（HMDFS 上 0700 临时目录无法写回的 CI-worker 适配，详见对话 #6 与问题表 #5；
先例 `archives/4/4ti2/1.6.10` 同法）。

## 依赖版本

| 依赖 | 版本 | 来源 | 说明 |
|---|---|---|---|
| openssl | 3.5.8.1 | ohpcd（静态包） | pen 的 TLS 前端/后端 |

## 上游测试：清点结论与实测

### 清点（R51 第一步，证据见 `reports/upstream-test-inventory.log`）

| 检查项 | 命令 | 结果 |
|---|---|---|
| 测试目录 | `find . -type d -iname 'test*' -o -iname 'testsuite'` | 空 —— 无任何测试目录 |
| automake 注册 | `grep -E 'TESTS\|check_PROGRAMS\|check_SCRIPTS\|check-local' Makefile.am configure.ac` | 无匹配 |
| Makefile.in 目标 | `grep -E '^(check\|test)' Makefile.in` | 只有 automake 自动生成的 `check-am: all-am` / `check: check-am` |
| 源码内测试宏 | `grep -rn 'RUN_TESTS\|#ifdef TEST\|TESTING\|assert\.h' --include='*.c'` | 仅 `pen.c:27 #include <assert.h>`（运行时防御性断言，非测试套件） |

→ **结论：pen 0.34.1 上游没有任何自动化测试入口。**

### 实测（R51 第二步）

上游唯一声明的测试入口是 `make check`，已在 OHOS 构建树内真实执行（原始输出见
`reports/upstream-test-run.log`；`conanfile.py` 的 `build()` 也会调用它，CI 日志可见
`pen/0.34.1: RUN: make check -j20`）：

| 项目 | 值 |
|---|---|
| 测试命令 | `make check`（`conanfile.py` build() 内自动执行） |
| 退出码 | 0 |
| 用例总数 | **0** |
| 通过 | 0 |
| 失败 | 0 |
| 跳过 | 0 |
| 输出 | 空（check-am 依赖 all-am 后无可执行动作） |

**这不是"测试被跳过"或"测试失败"**：automake 的 `check` = `check-am` = `all-am`，
未注册 `TESTS` 时没有任何测试程序被构建或运行，所以既无输出也无失败。
`test_package` 的 4 条用例**不计入**上述上游测试统计，另行汇报（下一节）。

## 新增鸿蒙消费者用例（4 条，非断言型）

需求要求"适配后的上游测试用例至少新增一个鸿蒙测试用例（消费者用例、验证可行性），且不能是断言"。
因此新增的是**真实跑通的数据面/控制面用例**，不写任何 `assert` 语句，每条都打印实际观察量：

| 用例 | 场景 | 命令 | 判据（真实观察量） |
|---|---|---|---|
| OHOS-T1 | UDP 数据面 | `penlog 127.0.0.1 17140` → `pen -U 17140 → 127.0.0.1:17141` → `penlogd 17141 -l <log>` | 负载均衡器把日志行透传给 penlogd，落盘内容与发送内容逐字一致（82 字节） |
| OHOS-T2 | TCP 控制面 | `penctl 127.0.0.1:17142 servers` | pen 的 TCP 控制口返回运行期服务表：`0 addr 127.0.0.1 port 17141 conn 1 ...`（`conn 1` 证明 T1 流量确被计入） |
| OHOS-T3 | TCP 数据面 | `penctl 127.0.0.1:17143 servers`（pen A 数据口 → pen B 控制口） | 经两跳 pen 转发取回的服务表与直连 B 控制口**字符串完全相同**（证明 TCP 双向中继正确） |
| OHOS-T4 | 统计面 | `pen ... -w stats.html` + `kill -USR1` | 生成 HTML 状态页（1564 字节），含 `Pen status page` / `1 servers` / 后端地址 |

- 用例实现：`test_package/test.sh`（`conan create` 时由 test_package 自动执行，CI 可见）
- 本机独立入口：`test_ohos/run_ohos_test.sh [<prefix>]`
- 实测输出：`reports/ohos-consumer-test.log`（`cases=4 failed=0`）

为什么不用外部 HTTP 服务（python/curl/busybox）做后端：pen 自带 `penlog`/`penlogd` 与
`penctl`，互相驱动即可构造完整往返，不引入 CI 环境依赖，测试完全自洽
（这也是 T3 用"pen 转发 pen 自己的控制口"的原因）。

### `penlogd` 日志落盘时机的实测记录

`penlogd` 用 `fopen(...,"a")` + 可选 `setvbuf`；实测传 `-b`（unbuffered）在 OHOS musl 下
仍要等进程关闭文件才在磁盘可见。因此用例采用**先 `SIGTERM` 优雅退出再读日志**
（`penlogd.c` 的 SIGTERM handler 清 `loopflag`，主循环退出后 `fclose(logfp)` 落盘）。
这不是缺陷，是上游 buffered I/O 的正常语义；用例按此设计，避免把"读得太早"误判为失败。

## 交付物

| 文件 | 大小 | 说明 |
|---|---|---|
| `bin/pen` | 4884928 B | 负载均衡器本体（静态链入 OpenSSL 3.5.8.1） |
| `bin/penctl` | 22912 B | 控制口客户端 |
| `bin/penlog` | 22912 B | web 日志 UDP 转发器 |
| `bin/penlogd` | 31104 B | 日志聚合守护进程 |
| `bin/mergelogs` | 31104 B | 离线日志合并 |
| `share/man/man1/*.1` | — | 5 个手册页 |
| `doc/pen/*` | — | README / HOWTO / AUTHORS / ChangeLog / COPYING / penstats |
| `licenses/COPYING` | — | GPL-2.0-or-later 许可证 |

### 产物属性与冒烟（G4 / L2 / L4 / L5 的手工补证）

`conan-verify` 的 G4/L2/L4/L5 在对纯可执行包（无 `lib/`、无 cache 可解析路径）时会打印
「无法找到程序包 ID / 无 cache 路径」并跳过。为不留下证据空洞，用 `llvm-readelf` 与真机
执行对 5 个产物逐一手工复核（复核对象：包 `bb90e580ad95…` 的 `bin/{pen,penctl,penlog,penlogd,mergelogs}`；
原始输出存本机 `pen-logs/elf-evidence.log`、`pen-logs/smoke-l2.log`，`.log` 按仓库惯例不入库，
关键结论已全部固化于下表，可对任意 OHOS 环境的产物重跑 `llvm-readelf -h/-d/-l` 复核）：

| 检查项 | 命令 | 观察到的一致结果（5/5） |
|---|---|---|
| 架构 / 类型 | `llvm-readelf -h` | `ELF64` / `AArch64` / `Type: DYN (Shared object file)`（PIE） |
| 运行期依赖 | `llvm-readelf -d`（NEEDED） | 仅 `libc.so`（OpenSSL 静态链入，无 `-lssl`/`-lcrypto` 动态依赖） |
| 加固属性 | `llvm-readelf -d`（FLAGS/FLAGS_1） | `BIND_NOW` + `NOW` + `PIE` |
| RELRO | `llvm-readelf -l` | `GNU_RELRO` 段存在（Partial RELRO + BIND_NOW） |
| 栈可执行性 | `llvm-readelf -l` | `GNU_STACK ... RW`（**无 E 位**，不可执行栈） |
| RPATH / RUNPATH | `llvm-readelf -d` | **均无**（无 `$ORIGIN` 依赖，无需重定位） |
| 冒烟（L2 口径） | `pen -h` / `penctl` / `penlog` / `penlogd` / `mergelogs` | 全部即刻打印 usage 并返回，**无挂起**（`timeout 5` 未触发） |

5 个产物的 `llvm-readelf -h` 头部实摘（复核用指纹）：

```
Class:                             ELF64
Data:                              2's complement, little-endian
Type:                              DYN (Position-Independent Executable file)
Machine:                           AArch64
```

> 说明：`pen` 上游没有 `--version`/`-v` 选项，`-v` 会被 getopt 判为 unrecognized 并打印
> 完整 usage（退出码 0）；`penlog` 无参数时打印 usage 且退出码 1。二者均为上游既有行为，
> 非适配引入，按最小改动原则不改。

## 注意事项

- **GeoIP 功能不可用**（`--without-geoip`）：制品仓无 libgeoip，仅影响统计页国家字段。
- **DSR（Direct Server Return）不可用**（`--without-dsr`）：依赖 netmap 用户态头，OHOS 无实现。
- 上游无测试，回归保护完全依赖本仓库新增的 4 条消费者用例；后续改动若破坏数据面会被 T1/T3 抓到。
- 交叉编译产物为 OHOS ELF，只能在 OHOS / 鸿蒙 PC 环境运行（本机即目标平台，用例已在本机实跑）。
- 命令行为依赖 `penlogd` 的 SIGTERM 优雅退出；若在容器/CI 中直接 SIGKILL，日志可能只存在于缓冲区。
---

**编译结束**: 2026-09-28 18:51
**最终状态**: published
