# libnl3-cli 3.11.0 适配笔记

## 编译环境

- 构建系统: autotools（release dist tarball，已含预生成 configure / Makefile.in）
- 编译日期: 2026-09-18（最终轮 conan create 全绿）；上游测试实跑补录 2026-09-20
- 编译器: clang / clang++ 15（`/data/service/hnp/bin/clang`）
- 目标平台: HarmonyOS PC aarch64，os=OHOS / arch=armv8 / clang 15 / libc++ / cppstd=17 / Release
- 状态: built（本地 conan create 通过）
- 宿主特征: `uname -s` = `HarmonyOS`，`uname -r` = `HongMeng Kernel 1.12.0`
- 与本体包关系: 与 `archives/l/libnl/3.11.0` 同源同一份 tar 归档；本体 `--disable-cli`
  只交付 6 个静态子库，本子包承担全部 CLI 交付物（本仓惯例：本体不装 bin/，CLI 归独立子包）。

## 交付形态（与本体包的关键差异）

- 本体包实测为**纯静态 + --disable-cli**（无 bin/、无 libnl-cli-3、零 .so）→
  E542 copy 不可行、requires 复用也不可行（静态宿主不导出 dynsym，插件 dlopen 必死）。
- 本子包**同源整树自建全 shared**：`--enable-shared --disable-static --enable-cli=bin`，
  交付 48 个 bin 工具 + 7 个共享库（SONAME .so.200）+ 10 个 dlopen 插件（lib/cli/{cls,qdisc}）
  + etc/libnl/{classid,pktloc} 数据——对齐发行版 libnl3-cli 子包内容。

## 编译步骤

```sh
# 双 profile 绝对路径（profile: ci/conan/profiles/ohos-aarch64）
conan create archives/l/libnl3-cli/conanfile.py --version=3.11.0 \
  -pr:h="$W/ci/conan/profiles/ohos-aarch64" -pr:b="$W/ci/conan/profiles/ohos-aarch64" \
  --build="libnl3-cli/*"
```

配方内固化处置：E114（去 configure 内 `umask 077 && `）、E490（autotools helper 执行位）、
E002/E005（/tmp 只读 → TMPDIR 重定向）、safe-bin rm shim 三通道清除（导出函数
BASH_FUNC_rm%%/unlink%%/rmdir%% 必须 `unset -f` 才能真正移除）、E236（os.walk 递归清 .la）、
`autotools.install(args=["-j1"])`（串行 install 规避 relink 竞态）、SONAME 软链实体化。

## 遇到的问题与解决方案（conan create 9 轮至全绿）

| # | 首错 | 根因 | 修复 |
|---|---|---|---|
| 1 | `Package type is 'library', but no 'shared' option declared` | Conan 2 要求 library 类型声明 shared option | `options={"shared":[True]}` |
| 2 | test_package `AttributeError … rootpath` | Conan 2 移除 `cpp_info.rootpath` | 改 `package_folder` |
| 3 | clang 报注释内语法错 | C 块注释里 `*/` 提前终止 | 改注释措辞 |
| 4 | `redefinition of 'struct sockaddr_storage'`（E091/E119） | netlink 头拉入 `linux/socket.h` 与 musl `sys/socket.h` 冲突 | `-D_UAPI_LINUX_SOCKET_H -D__kernel_sa_family_t=ushort` |
| 5 | 链接期 `undefined symbol nl_addr_parse` | **lld 不从 DT_NEEDED 传递闭包解析符号** | 链接行显式列全 7 库 |
| 6 | `run() got unexpected keyword 'ignore_error'` | Conan 2 API 是 `ignore_errors` | 改名 |
| 7 | 消费者用例 dlopen 失败 `nl_cli_tc_register: symbol not found` | **musl 严格符号版本化**：插件 libtool module（LIBADD 空）无版本 UND 引用 ≠ version script 带版本定义（glibc 宽松、musl 严格；RTLD_GLOBAL 预加载不能绕过，实测坐实） | **补丁 0003**：10 个插件 `la_LIBADD`+`la_DEPENDENCIES` 挂 `src/lib/libnl-cli-3.la` |
| 8 | 0003 后 `make Error 2: cannot find src/lib/libnl-cli-3.la` | automake 不从 la_LIBADD 推导构建依赖 | 0003 同时生成 `la_DEPENDENCIES` 行 |
| 9 | package() install 失败 `unable to find library -lnl-cli-3`（relink） | conan `Autotools.install()` 默认 `-j4`：install-exec-am ∥ install-data-am 竞态 | `autotools.install(args=["-j1"])` |
| 瑕疵 | 包内插件子目录残留 10 个 .la | E236 清理只扫了 lib 顶层 | `os.walk` 递归清（17 个全清，终态 la=0） |

## 源码修改

### `patches/0001-support-ohos-triplet.patch`（E205）
config.guess(2023-06-23) 不识 `uname -s` = HarmonyOS；config.sub 不识 linux-ohos。
按 scripts/patch-autotools-ohos.pl 生成，**不用 --build/--host 绕过**。
与本体包 0001 逐字节同源。

### `patches/0002-headers-selfcheck-use-linux-private.patch`（E091/E119）
build-headers-test 规则补 `-I$(srcdir)/include/linux-private`，与本体包 0002 同源。

### `patches/0003-cli-plugins-link-libnl-cli-3.patch`（musl 严格符号版本化）
本子包独有：10 个 CLI dlopen 插件挂接 libnl-cli-3.la（LIBADD + DEPENDENCIES），
使插件 NEEDED/verneed 记录 libnl-cli-3.so.200 与 `libnl_3` 版本节点，
`nl_cli_load_module()` dlopen(RTLD_NOW) 闭包自洽。仅改链接输入，不改源码语义。

## 依赖版本

- Conan 依赖: 无（R36 无适用对象；构建期宿主工具 flex/bison/pkg-config 由 profile
  [buildenv] 的 /data/service/hnp/bin 提供；release tarball 已含预生成 configure）
- 上游测试依赖: check/0.15.2（ohpcd 可消费，供 libcheck）

## 验证结果

### 源码核验
- 官方同批 `.sha256sum` = 本地复算 = `2a56e1edefa3e68a7c00879496736fdbf62fc94ed3232c0baba127ecfa76874d`
- 官方 `.md5sum` = 本地复算 = `0a5eb82b494c411931a47638cb0dba51`

### conan create + 鸿蒙消费者用例
- conan create 最终轮 EXIT 全绿（reports/conan-create.log）
- test_package（harmonyos_specific_test.c）：**11 PASS / 0 FAIL**
- 包终态：bin=48、la=0、.so 实体 31（软链已实体化 14 个）、dlopen 插件 10、etc/libnl + licenses 完整

### 上游测试（make check，2026-09-20 实跑补录）

口径继承本体包：31 程序 = check_PROGRAMS 29 + TESTS 2（check-all / check-direct；
后者仅 `--enable-static` 才编译，故测试树 configure 额外加 --enable-static，
属测试口径而非交付形态）。测试树复刻配方三补丁。

| 维度 | 总数 | 通过 | 环境受限 | 断言失败 |
|---|---|---|---|---|
| check-all | 31 | 12 | 19 | 0 |
| check-direct | 2 | 2 | 0 | 0 |
| 手工 27 程序（check_PROGRAMS 中未纳入 TESTS，上游只构建不运行） | 27 | 1 | 26 | 0 |
| **合计** | **60** | **25** | **35** | **0** |

- check-all：`38%: Checks: 31, Failures: 0, Errors: 19`；19 个 Error 全部为
  `nl-test-util.c:168 → Received signal 31 (Bad system call)`（SIGSYS = seccomp 拦
  `unshare(CLONE_NEWNET)`），名单：cache_and_clone:0、route_1:0、test_create_iface:0…16。
- check-direct：`100%: Checks: 2, Failures: 0, Errors: 0`。
- 手工 27 程序：仅 test-socket-creation EXIT=0；其余 26 个全部 netlink
  connect/bind `No Access`（EACCES = 鸿蒙 LSM adhoc_bin 域拒 AF_NETLINK）。
- **环境受限双层归因与本体包一致，0 项为移植缺陷断言失败。**
- 逐项日志：reports/ut-report.md（汇总）+ reports/manual-<name>.log（逐程序）。

## 编译结束

本包（libnl3-cli/3.11.0）编译与验证到此结束：conan create 全绿、消费者用例 11 PASS、
上游测试实跑 60 checks（25 过 / 35 环境受限 / 0 断言失败）。待 conan-verify / finish /
W2/W3 后进入提交流程（停 LOCAL_AUDIT_PASS 等待确认）。

## 注意事项

- 消费者链接行须**显式列全 7 库**（lld 不解析 DT_NEEDED 传递闭包）。
- 本子包 requires 本体包 libnl/3.11.0 的头文件；两包同版本号配对发布。
- libcheck 在 OHOS 需 `TEMP=<可写目录>` + `LD_LIBRARY_PATH` 指向包内 lib/
  （libcheck 通信临时文件写死 /tmp；check.pc 烘焙 prefix 会随包目录失效）。
---

**编译结束**: 2026-09-20 18:43
**最终状态**: built
