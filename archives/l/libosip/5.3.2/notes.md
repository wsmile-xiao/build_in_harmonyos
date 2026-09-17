# libosip 5.3.2 适配笔记

- 上游: GNU oSIP <https://www.gnu.org/software/osip/>
- tarball: libosip2-5.3.2.tar.gz (730080 B)
- License: LGPL-2.1-or-later（以 tarball 内 COPYING 为准；历史归档
  libosip2/5.3.1 manifest 记录 GPL-2.0 系误记，GNU osip 官方为 LGPL）

## 包名说明

包名 `libosip` 与分支 `feat/libosip-5.3.2` 一致；上游 tarball/AC_INIT 名为
`libosip2`，构建产出两个库，均收进本包：

| 库 | SONAME | 层 |
|----|--------|-----|
| libosip2 | libosip2.so.15 | 事务/状态机层 (`osip2/osip.h`) |
| libosipparser2 | libosipparser2.so.15 | SIP 消息解析层 (`osipparser2/osip_parser.h`) |

`-version-info 15:1:0` → SONAME `*.so.15`（构建后 readelf 实测）。

## 依赖

纯 C，无第三方 conan 依赖。系统库：pthread（可选项，默认开）、
librt（clock_gettime）；libsocket 仅非 Linux 平台（OHOS 不涉及）。
musl 提供 pthread/rt。

## 适配要点（conanfile.py + 1 个源码补丁）

1. **E007 config.guess/config.sub**：tarball 内为 2014-03-23（guess）/
   2014-09-11（sub）版，不识别 `aarch64-unknown-linux-ohos`：HarmonyOS
   下 `uname -s` 返回 `HarmonyOS`，旧版 config.guess 直接猜测失败
   （rc=1，"unable to guess system type"）；config.sub 则报
   "machine aarch64-unknown-linux not recognized"。修复改为补丁
   `patches/0001-config-guess-config-sub-ohos.patch`（conandata.yml
   登记，source() 中 apply_conandata_patches 应用）：config.guess 在
   `aarch64:HarmonyOS:*:*` 输出 `aarch64-unknown-linux-ohos`，config.sub
   增加 `-linux-ohos*` OS 模式。configure 由 generate() 显式传入
   `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`
   （各一次），不再执行猜测路径。注意：不能像 libnet 那样用
   `--build=aarch64-unknown-linux-gnu` 绕过 —— GNU 构建系统要求
   build/host 一致或明确交叉声明，直接沿用 ohos 三元组更正确（本机即
   OHOS aarch64，原生构建）。不再复制主机 automake 的 config.guess/
   config.sub —— 原生 automake 1.16 同样不认识 HarmonyOS，且 CI worker
   未必装了 automake share 目录（glob 为空时整段静默失效，正是 PR #9921
   远端失败根因：worker 干净环境下旧脚本直接报 cannot guess）。
2. **E011 umask 077**：HMDFS uid 映射下 `umask 077` 创建的 config.status
   临时目录不可写（`can't create ./confXXXX/subs1.awk: Permission
   denied`）。对 configure/config.status 做 `umask 077 → umask 022` 文本
   替换，并对 tarball 解包树补写权限位。
3. **install-sh 单文件限制（新知识草稿 DRAFT-E574）**：OHOS 无
   `/usr/bin/install`，configure 回退到 tarball 内 1991 版
   scripts/install-sh（"can only install one file at a time"，src 只取
   第一个文件、多余参数静默丢弃、rc=0）；automake-1.16 `am__base_list`
   每批 64 文件一次调用 → 每批只装第 1 个，3 个头文件目录各 1 批 =
   恰好 3 个文件（修复前 3 → 修复后 31）。与 hmdfs 无关（tmpfs 同样
   复现，目录覆盖说法已删除）。替换为主机 automake-1.16 版 install-sh
   （连同 config.guess/sub、missing、compile、depcomp）后全部正确安装。
4. **无 RPATH（新知识草稿 DRAFT-E575）**：libtool 默认把 `$libdir` 的绝对
   路径作为 DT_RUNPATH 写入 .so。无 patchelf 且 lld 无 `--no-rpath`
   选项（实测 `-Wl,-rpath,` 空参数会报 `undefined symbol: main`），
   采用：configure 之后、make 之前，将生成的 `libtool` 脚本中
   `hardcode_libdir_flag_spec="\$wl-rpath \$wl\$libdir"` 置空。
   实测：两库均无 DT_RUNPATH，SONAME/NEEDED 完好，torture 套件全过。
   副作用：构建树内测试程序需 `LD_LIBRARY_PATH` 指向 `.libs` 目录，
   在 `_run_upstream_tests()` 中统一设置。
5. **make check 相对路径不可用**：hmfs 上 Makefile 的
   `./$(top_srcdir)/src/test/tst` 相对执行报 inaccessible；改为配方内
   `sh <绝对路径>/tst <绝对路径>/res [-c]`，与 make check 内容完全一致。
6. **E002 /tmp 只读**：测试输出重定向到 `$TMPDIR`。
7. **.codesign**：OHOS clang 链接时自动加 .codesign 段（构建树签名）；
   package() 中 `objcopy --remove-section .codesign` 后
   `binary-sign-tool sign -selfSign 1` 重签（同 libxml2/2.15.3）。

## 上游测试（全部实测）

`--enable-test`（默认 no）后构建：

- `make check`（src/test）：`tst` 脚本驱动 `torture_test` 跑 161 个
  res/ 数据文件 —— **122 用例全过**（99 个 `sip*` + 23 个
  `sip-malformed*`），普通模式与 `-c`（clone）模式均过。
- 10 个 noinst 单项程序（不在 TESTS 中，需手动带 `res/` 运行）：
  turl tfrom tto tcontact tvia tcallid tcontentt trecordr troute twwwa
  —— **全部 rc=0**。注意二进制名与源文件名不同：`turls.c → turl`。
- `res/torture_sdps` 是已删除的 torture_sdp 程序的孤儿数据，非套件成员。

统计口径：122 torture 用例（普通 + clone 两种模式）+ 10 单项程序，
100% 通过；未删测试、未放宽断言。

## 消费者测试（test_package）

- `test_consumer.c`：公开 API 覆盖 SIP 解析（带 SDP 的完整 INVITE）、
  生成与往返（REGISTER 生成→重新解析）、response 生成（200 OK）、
  URI 解析/序列化、header 访问（To/From/CallID/CSeq/Via/Contact/
  Max-Forwards）、body/SDP、畸形输入拒绝（垃圾/截断/坏 URI）、
  osip2 事务层 init —— **54 checks / 0 failures**。
- `conanfile.py::test()`：OHOS 平台校验 —— AArch64 ELF、musl
  （NEEDED libc.so）、SONAME `*.so.15`、.codesign 存在、无 RPATH/RUNPATH；
  静态包则校验两个 .a 存在。
- 关键 API 陷阱（libosip 专用使用契约，非通用适配知识）：
  `parser_init()`；`set_method/set_version/set_reason_phrase` 不拷贝
  字符串，必须传 `osip_strdup` 的堆串；`osip_body_t.body` 非 NUL 终止；
  从 request 造 response 要先清 `sip_method`。

## 已知坑

- toybox grep 不支持 BRE `\|`（静默无输出），管道中用 `grep -E`。
- `~/.curlrc` 设了 15s max-time，下载用 `curl -q` 绕过。

## 结束

**编译结束**: 2026-09-11
**最终状态**: built
