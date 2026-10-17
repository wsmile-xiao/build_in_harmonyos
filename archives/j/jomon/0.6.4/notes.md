# jomon 0.6.4 适配笔记

## 编译环境

- 构建系统: makefile（上游自制 configure(bash) + Makefile，非 autoconf 生成）
- 编译日期: 2026-10-01
- 编译器: clang/clang++（OHOS SDK native 15，triplet `aarch64-linux-ohos`）
- 状态: built

## 编译步骤

```bash
# 配方全流程（host/build 使用同一 OHOS profile，与 CI 同口径）
conan create . --build=missing -pr:h ohos-aarch64 -pr:b ohos-aarch64
# 本地 CI 口径复核（L0/L1/L2/L5 pass、L4 warn；.ci-result.json exit_code=0）
ci/conan/build_and_test.sh jomon/0.6.4
```

- configure 关键选项：`--disable-geoip`（关闭可选依赖 GeoIP）
- 构建期工具：`re2c/4.3.1`（生成 `bpf/bpf_lexer.c`、`bpf/pcap_lexer.c`）、`python3`
  （`scripts/genprotocols.py` 生成 `decoder/decoder.h`、`decoder/register.h`）
- 链接依赖：`ncurses/6.6`（静态）
- 编译环境通过 `AutotoolsToolchain` 注入；**不能**用 `make CFLAGS=...` 覆盖（命令行赋值会让
  Makefile 内 `CFLAGS += -std=gnu11 -fwrapv ...` 失效）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 的 `check_ncurses` 失败退出 | 自制 configure 的能力探测只调裸 `$CC`，交叉编译时看不到 conan 依赖的头文件/库路径 | 补丁 0002：探测命令带上 `$CFLAGS $CPPFLAGS ... $LDFLAGS` |
| 2 | `VERSION` 为空，编译报未定义 | tarball 内无 `.git`，configure 用 `git describe` 取版本 | 补丁 0002：支持 `JOMON_VERSION` 注入；配方传 `self.version` |
| 3 | `-lncurses` 链接失败 | conan 的 ncurses 包只提供宽字符库 `libncursesw` | 补丁 0002 + 0001：探测与链接改用 `-lncursesw` |
| 4 | 链接时找不到依赖库 | Makefile `LIBS :=` 覆盖环境值且未带 `$(LDFLAGS)` | 补丁 0001：`LIBS := -lncursesw -lrt $(LDFLAGS)` |
| 5 | `qsort_r` 未定义 | OHOS musl 无 GNU `qsort_r`（仅 glibc 提供） | 补丁 0003：`portability.h` 加 shim（`#ifndef __GLIBC__`，单线程语义；jomon 本身单线程） |
| 6 | sysroot 头文件冲突（`sys/socket.h`、`linux/if_ether.h`） | 同一头文件在 OHOS sysroot 下按 libc 宏分支 | 配方 `generate()` 注入 `-D__MUSL__ -D__UAPI_DEF_ETHHDR=0`（**不**注入 `__OHOS__`） |
| 7 | `make install` 不可用 | OHOS 无 GNU install 命令（上游用 `install -sD`） | 配方 `package()` 用 conan `copy` 落盘 `bin/jomon`、`licenses/LICENSE` |
| 8 | 平台实现选择错误 | `MACHINE := $(shell uname -s)` 在 OHOS 上得到 `HarmonyOS` | 配方 `build()` 显式传 `MACHINE=Linux`（复用 Linux netlink/procfs 实现） |

## 源码修改

| 补丁 | 修改内容 |
|------|----------|
| `0002-configure.patch` | 能力探测带上编译/链接参数；支持 `JOMON_VERSION` 注入；探测宽字符 ncurses |
| `0001-Makefile.patch` | 链接宽字符 ncurses，并让链接行带上 `$(LDFLAGS)` |
| `0003-portability.h.patch` | 非 glibc libc 的 GNU `qsort_r` shim |

除上述补丁外无其他源码修改；词法器与协议表在构建时由 re2c、python3 生成。

## 依赖版本

| 依赖 | 版本 | 类型 |
|------|------|------|
| ncurses | 6.6 | 链接依赖（静态，避免与系统同名库冲突） |
| re2c | 4.3.1 | tool_requires（构建期） |
| python3 | 3.x（构建环境自带） | 构建期脚本 |

## 验证结果

```bash
conan create . --build=missing -pr:h ohos-aarch64 -pr:b ohos-aarch64   # EXIT=0
# test_package: test.sh 3/3 checks passed
bin/jomon --version              # jomon version 0.6.4
bin/jomon -ddd -f 'tcp or icmp'  # 输出 10 条 BPF 指令
```

详细测试记录（含上游 27 项单元套件实测结果 **24/27**）见本节命令、下方「注意事项」与
`reports/test-report.md` 第 5 节；`reports/` 下是本机 W3 运行产物，不作为本 PR 的交付物。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/jomon` | 唯一产物（CLI；软件级 `archives/j/jomon/commands.json` 已声明） |
| `licenses/LICENSE` | 上游 MIT 许可 |

## 注意事项

- 上游未实现完整 tcpdump 语法：`ip`/`tcp`/`udp`/`arp`/`icmp` 可用，`port`/`host`/`ether`
  不支持（jomon 自带手写过滤器编译器，不依赖 libpcap），**非平台适配缺陷**。
- 实时抓包需 `CAP_NET_RAW`/root；`-d/-dd/-ddd` 反汇编与 `-r` 离线分析不需要。
- 上游单元套件（`make test`，libcheck，27 项）已在 aarch64 OHOS 实测：**24 通过 / 3 失败**
  （88.9%）。3 项失败均为 `tests/decoder_test.c:69` 文本输出比对，仅首列时间字段不同（随宿主
  时区变化，`TZ=UTC` 复跑同样失败），解码正文一致，**非平台适配缺陷**；CI 仍未纳入该套件，
  本包 CI 以 test_package 集成用例验证（3/3）。
  复现三要点：`make test MACHINE=Linux`（命令行赋值，Makefile 的
  `MACHINE := $(shell uname -s)` 覆盖环境变量）、先 `python3 scripts/genprotocols.py` 生成
  `decoder/decoder.h`（`test` 目标无该依赖）、`TMPDIR`/`TEMP`/`TMP` 指可写目录
  （libcheck 用 `tmpfile()`，本机 `/tmp` 只读，否则 `check_msg.c:317` 报错）。

---

**编译结束**: 2026-10-01
**最终状态**: built
