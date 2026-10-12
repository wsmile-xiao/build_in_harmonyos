# mtu 1.5.1 适配笔记

## 概述

- 上游：https://github.com/ncopa/pingu（tag v1.5.1，tarball 31574 字节，sha256 见 conandata.yml）
- 本包：只交付 pingu 源码树中的 `mtu` 目标（二进制 `bin/mtu`），不含 pingu 守护进程与 pinguctl
- 类型：命令行工具（MTU 探测 `-d`/`-D`、注入 `-i`/`-I`，基于 raw ICMP socket + rtnetlink）
- 构建系统：手写 Makefile（custom/makefile）
- 许可证：GPL-2.0-or-later（Gentoo ebuild 标注 GPL-2+；上游仓库未附 LICENSE 文件）
- 状态：built（待真机 rule4 门禁）

## 源码结构（pingu-1.5.1）

- `src/mtu.c`：mtu 主程序（getopt 解析 `-DdIi:`，usage 退出码 3）
- `src/icmp.c` / `src/icmp.h`：raw ICMP 收发（`SOCK_RAW/IPPROTO_ICMP`，`IP_MTU_DISCOVER`）
- `src/netlink.c` / `src/netlink.h`：rtnetlink 路由查询（`NETLINK_ROUTE`，`RTM_GETROUTE/RTM_GETLINK`）
- `src/Makefile`：`BIN_TARGETS = mtu`，`mtu_OBJS = mtu.o netlink.o icmp.o`
- 顶层 `Makefile` + `configure`：为 pingu 守护进程服务（含 libev 探测）；mtu 目标不需要它们

## 依赖处理

- mtu 目标**零外部依赖**：仅需 libc + Linux 内核头（`linux/if.h`、`linux/sockios.h`、`linux/netlink.h`、`linux/rtnetlink.h`、`asm/types.h`、`netinet/ip*.h`）
- 上游 `configure` 会硬要求 libev（`die "libev is required"`，为 pingu 守护进程的 `ev.h` 探针），但 mtu 并不链接 libev
- 因此配方**跳过 configure**，直接 `make -C src mtu CC=<conan conf 编译器> PINGU_VERSION=1.5.1`（R33：编译器取自 `tools.build:compiler_executables:c`）
- `dependencies: []`，无 `requires`，W0/R36 干净

## 构建命令（真机复现）

```bash
cd archives/m/mtu/1.5.1
conan create . --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

配方 `build()` 等价于：

```bash
make -C src mtu -j1 CC="<profile 注入的 clang>" PINGU_VERSION="1.5.1" PACKAGE_VERSION="1.5.1"
```

`package()` 直接用 conan `copy` 把 `src/mtu` 装到 `bin/mtu`（不走上游 `make install`，规避 OHOS 上 toybox install 的多源限制），并把上游 `README.md` 装到 `licenses/`。

## 上游测试审计（R51 三步法第 1 步）

| # | 审计源 | 结论 |
|---|--------|------|
| 1 | 源码树（root/src/doc，无 tests/test 目录） | 无任何 `tests/`、`test/`、`*_test.c` |
| 2 | `src/Makefile`、顶层 `Makefile` | 仅 `all/install/clean`，无 `check/test/TESTS` 目标 |
| 3 | `configure --help` | 仅 debug/warnings/werror/lua/doc 选项，无测试开关 |

结论：上游 1.5.1 **无自动化测试套件**（`upstream_tests_exist: false`，`upstream_test_total: 0`，口径 `autotools_tests`：手写 Makefile 无 TESTS 注册，`make check` 无规则，等价于空 automake check 目标）。`build()` 与 `test_package` 均输出 `status: no_tests` 的 `HMBS_UPSTREAM_TEST_RESULT`（discovered/executed/passed/failed/skipped 全 0，附 reason）。

## test_package（消费者视角，R34）

`test_mtu.sh <bin/mtu>` 共 4 条断言（无需 raw socket 与网络，防 toybox 空文件假绿）：

1. 裸 `mtu` 走 usage 路径退出码 3
2. 未知选项 `mtu -z` 走 usage 路径退出码 3
3. usage 输出非空
4. usage 输出含 `usage: mtu` 与 `-d` 旗标文档

脚本以 `RESULT: P passed, F failed` 结尾，`test_package/conanfile.py` 用正则解析该行生成 `HMBS_TEST_PACKAGE_RESULT`（discovered/passedCount 为真实计数），失败时抛异常使 `conan create` 变红。

反假绿说明：若把二进制换成 `exit 1` 桩，断言 1/2 的退出码检查立即失败，harness 可抓到失败；输出非空与旗标检查防止拿空文件比空文件。

## OHOS 风险点（待真机验证）

- `asm/types.h`（`__u8`）：musl 下可能缺失，若真机报 `fatal error: asm/types.h`，改用 `linux/types.h` 或 `stdint.h` 兼容补丁（POSIX 方式，不用 `__OHOS__` 宏，R8 合规）
- `linux/` 内核头：OHOS SDK 应自带；缺失则按同类库经验补最小 shim
- `gethostbyname`：已废弃但 musl 仍提供，编译应只有 deprecation 警告
- raw socket：仅运行时需要，构建与 test_package 均不触碰；`mtu -d` 真实探测留给用户在有 `CAP_NET_RAW` 的环境手动执行

## 已知限制

- `mtu -d/-D/-i/-I` 真实模式需 `CAP_NET_RAW` + 网络，test_package 未覆盖（headless 包测试无法依赖网络与特权 socket）
- 上游无 `--version` 旗标，版本校验通过 `PINGU_VERSION=1.5.1` 编译期注入与包版本号一致性保证
- `commands.json` 已按 R38 在软件级目录声明（type tool，binary true）

## 验证结果

- 本地：Windows 工作机不运行 conan（按任务守则由真机预检）；待 HMBS 真机 `conan create` 日志回填通过率
- 上游测试用例通过率：0/0（上游无测试，`no_tests`，见上）
- 新增测试用例通过率：待真机 evidence 轮填写（本地不猜测）
