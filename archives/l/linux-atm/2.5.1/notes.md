# linux-atm 2.5.1 适配笔记

## 编译环境
- 构建系统: autotools（源码自带 `configure`，无需 autoreconf）
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4（OHOS SDK 26.0.0.18，lld 链接）
- 状态: built（conan create / conan-verify 全绿）

## 编译步骤

```bash
source .build-context-linux-atm-2.5.1
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX          # 自动 --disable-shared --enable-static
make -j1                                      # 必须串行，见问题 #8
make check -j1                                # L1 上游测试：构建并执行 src/q2931/q.test
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess: unable to guess system type` | 2009 版 config.guess 不认识 `uname -s = HarmonyOS` | 在 config.guess 增加 HarmonyOS 分支，输出 `aarch64-unknown-linux-ohos`；config.sub 接受 `linux-ohos` 三元组 |
| 2 | 生成的 `config.status` 报错 `can't create ./confXXXXXX/subs1.awk: Permission denied` | configure 生成 config.status 时用 `umask 077 && mktemp -d`，0700 目录在 HMDFS 上因 UID 映射不可写（知识库 E011） | 把 configure 中 `umask 077` 改为 `umask 022` |
| 3 | `ld.lld: undefined reference: blli_in_use` | 上游 2.5.1/2.5.2 在 sapequal.c/sap2text.c/sigd/sap.c 调用 `blli_in_use()` 却从未定义；GNU ld 的 `--allow-shlib-undefined` 掩盖了它，lld 默认拒绝 | `src/include/atmsap.h` 补 `static __inline__ int blli_in_use(struct atm_blli)` |
| 4 | `ld.lld: unable to find library -lfl` | 4 个 scanner 链接 `-lfl`（flex 运行库），OHOS 工具链不带 libfl | 4 个 `.l` 加 `%option noyywrap`，并从 5 个 Makefile.in 去掉 `-lfl` |
| 5 | `ld.lld: undefined symbol: atmpvc_addr_in_use / atmsvc_addr_in_use` | 现代内核头（含 OHOS sysroot）已删除 `<linux/atm.h>` 里的这两个 inline 辅助函数 | 在 `src/include/atm.h` 中恢复这两个 inline 定义 |
| 6 | `ld.lld: undefined symbol: on_exit` | `on_exit()` 是 glibc 扩展，OHOS（musl）不提供 | atmsigd 改用可移植的 `atexit()` |
| 7 | `error: redefinition of 'sockaddr_storage'` | OHOS musl 的 `<sys/socket.h>` 与内核头 `<linux/socket.h>` 都定义 `struct sockaddr_storage`，`linux/if_arp.h → netdevice.h → if.h → socket.h` 链式包含触发冲突 | 相关 TU 预定义 `_UAPI_LINUX_SOCKET_H` 阻断内核版本，并补 `__kernel_sa_family_t`（其他内核头仍需要它） |
| 8 | `ql_l.l: fatal error: 'ql_y.h' file not found` | qgen 的 flex 输出 ql_l.c 依赖 bison 生成的 ql_y.h，但 make 未声明该依赖，`-j2` 竞态 | 配方中 `make -j1` 串行构建 |
| 9 | `ld.lld: duplicate symbol: now` | libatm（timer.c）与 sigd/io.c、arpd/io.c 都定义了全局 `struct timeval now`；共享库下靠符号插入掩盖，静态链接在 `-fno-common`（clang ≥ 11）下报重复 | 删除 sigd/io.c、arpd/io.c 中重复的试探性定义，统一使用 libatm 的定义（atmd.h 已 `extern` 声明） |

## 源码修改

- `config.guess` / `config.sub`：新增 HarmonyOS / linux-ohos 识别（补丁 0001、0002）
- `configure`：`umask 077` → `022`（补丁 0003）
- `src/include/atm.h`：`_UAPI_LINUX_SOCKET_H` 守卫 + 恢复 `atmpvc/atmsvc_addr_in_use`（补丁 0007）
- `src/include/atmsap.h`：补 `blli_in_use()`（补丁 0008）
- `src/{arpd,oamd}/*.c`：`_UAPI_LINUX_SOCKET_H` 守卫（补丁 0004-0006、0009）
- `src/qgen/ql_l.l`、`src/sigd/cfg_l.l`、`src/switch/cfg_l.l`、`src/test/ispl_l.l`：`%option noyywrap`（补丁 0011、0014、0016、0020）
- `src/{qgen,sigd,switch/debug,switch/tcp,test}/Makefile.in`：去掉 `-lfl`（补丁 0010、0012、0017、0018、0019）
- `src/sigd/atmsigd.c`：`on_exit()` → `atexit()`（补丁 0013）
- `src/sigd/io.c`、`src/arpd/io.c`：删除重复的 `struct timeval now`（补丁 0015、0005）

## 依赖版本

无 Conan 依赖（只依赖 libc）。构建期使用工具链自带 clang/lld、flex 2.6.4、bison、perl、make。

## 验证结果

```bash
$ python3 scripts/ohc-run.py conan-verify linux-atm 2.5.1
G0 PASS / G1 PASS / G2 PASS(conan create) / G3 PASS / G4 PASS / L2·L4·L5 PASS

# test_package
1/1 Test #1: test_linux_atm ... Passed    (libatm: text2atm/atm2text/atmpvc_addr_in_use/sap_equal/sockaddr_storage)
OHOS smoke test: .../p/bin/atmsigd -V  ->  2.5.1
```

## 上游测试情况（真实核验）

上游唯一测试入口是 `src/q2931` 声明的 `check_PROGRAMS = q.test`（Q.2931 消息表字段/组/取值
碰撞检查），命令 `make check`。原始状态该入口不可运行，本 PR 修复后已真机执行并通过：

1. **构建接线错误**：`q_test_SOURCES = qtest.c`，而真正需要编译的是 qgen 生成的 `q.test.c`
   （`qtest.c` 只提供 `main`，由 `q.test.c` `#include`）。直接编译 `qtest.c` 会因
   `fields/groups/unique` 未声明而失败；且 `#TESTS = $(check_PROGRAMS)` 被注释，
   `make check` 只构建、不执行。
   修复：补丁 `0021-src-q2931-Makefile.in.patch`（`q_test_SOURCES = q.test.c`、
   启用 `TESTS`、补 `check-TESTS` 运行器）。
2. **碰撞表误报**：qgen 生成的 `q.test` 检查表把「同一个 IE 被多实例化」
   （`msg.fmt` 中 `blli1/blli2/blli3`、`cause/cause2`、`git/git2/git3` 指向同一个 `ie_*` 块）
   造成的字段名重复、以及 `multi` 选择器（`_ie_id`）中按设计重复的取值，当作碰撞报错
   （退出码 1）。这些重复是「一条消息内允许出现多个同类型 IE」的设计，不是表错误。
   修复：补丁 `0022-src-qgen-first.c.patch`（字段名表只发射共享结构的首个实例）、
   `0023-src-qgen-second.c.patch`（取值唯一性只对 `case` 选择器检查）。
   **补丁只改变生成的 `q.test.c`（检查程序）；库产物 `q.out.c`/`q.out.h` 逐字节不变**
   （已用原始/修复后 qgen 对同一预处理输入对拍验证）。
3. **真机执行结果**：`make check` → 构建 `q.test`（`q.test.c` → `q.test.o` → `q.test`）并执行，
   输出 `=== upstream test: q.test ===`、无 collision、退出码 0 → **1/1 PASS**。

结论：上游测试入口 1 个（`src/q2931/q.test`），适配后真机执行 1 个、通过 1 个（**1/1**）。

## 注意事项

- `make` 必须串行（qgen 的并行竞态）。
- `q.test` 原状不可运行（构建接线错误 + 碰撞表误报），已由补丁 0021-0023 修复并接入 `build()`
  （`make check`）；库产物不受影响（`q.out.c`/`q.out.h` 逐字节不变）。
- 构建日志中 `error: write on a pipe with no reader` 来自 Makefile 解析期的 `$(shell $(CC) -E ... | awk -f script.awk)`：awk 用 `nextfile` 提前停止读取，clang 收到 SIGPIPE 打印该消息，不影响 `default.nl` 生成与构建结果。
---

**编译结束**: 2026-09-26 13:02
**最终状态**: built
