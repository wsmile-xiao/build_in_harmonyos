# ocproxy 1.6 上游测试清点

本文件回答一个门禁问题：**本包构建实际运行了多少条上游测试？** 结论先行：

| 口径 | 数值 | 说明 |
| --- | --- | --- |
| 上游框架实际注册的用例数（可运行入口） | **0** | `configure` 生成的 `Makefile` 里没有任何 check 相关目标 |
| 本次实际运行数 N′ | **0** | 构建与 `test_package` 都不运行上游代码的测试 |
| 随 tarball vendored 的 lwIP 单元测试用例 | 22 | 依赖 Check 框架，且构建系统完全不引用，属死代码 |

因此正文与 manifest 申报的**上游测试通过率写作 `0/0（上游无可运行测试入口）`**，
不把 vendored lwIP 的 22 个用例计入分母（它们不是 ocproxy 的测试，也不会被编译）。

## 1. 取数命令与原始输出

### 1.1 `Makefile.am` 没有任何测试目标

```sh
$ grep -n 'TESTS\|check_PROGRAMS\|check-local\|check:' Makefile.am
（无输出）
$ grep -c '' Makefile.am
142
```

`Makefile.am` 只声明 `bin_PROGRAMS = ocproxy`，以及在 `ENABLE_VPNNS` 条件成立时追加
`vpnns`；`ocproxy_SOURCES = $(LWIP_SOURCES) $(APP_SOURCES)`。

### 1.2 `configure.ac` 没有测试宏

```sh
$ grep -n 'check\|test' configure.ac
23:if test "x$enable_debug" = xyes; then
45:if test "x$enable_vpnns" = xyes; then
50:AM_CONDITIONAL([ENABLE_VPNNS], [test "x$enable_vpnns" = xyes])
```

三处都是 shell 的 `if test` / 条件变量，没有 `AC_CONFIG_TESTDIR`、`AM_PATH_*` 之类的
测试框架接入，也没有 `check` 目标。

### 1.3 vendored lwIP 的用例数

```sh
$ grep -c '^START_TEST' lwip/test/unit/*/*.c
lwip/test/unit/core/test_mem.c:1
lwip/test/unit/core/test_pbuf.c:3
lwip/test/unit/dhcp/test_dhcp.c:4
lwip/test/unit/etharp/test_etharp.c:1
lwip/test/unit/tcp/tcp_helper.c:0
lwip/test/unit/tcp/test_tcp.c:7
lwip/test/unit/tcp/test_tcp_oos.c:5
lwip/test/unit/udp/test_udp.c:1
（合计 22）
```

### 1.4 这些用例不会被编译或运行

```sh
$ grep -n 'lwip' Makefile.am | grep -i test
（无输出）
$ grep -rn 'lwip/test\|check_PROGRAMS\|TESTS' Makefile.am configure.ac
（无输出）
```

上游把 lwIP 当作 vendored 库：`LWIP_SOURCES` 只包含 `lwip/src/**` 与
`contrib/ports/unix/**`，`lwip/test/` 整个目录不参与构建。`lwip_unittests.c` 依赖
`lwip_check.h`（Check 框架），而 ocproxy 本身也没有引入 Check 的 `configure` 探测。

## 2. 为什么不用 `only 0 tests` 一句话带过

按 R51 三步法，分母必须是「清点所得的上游测试总数」，并逐项归因候选数法的差额。
这里的候选口径有两个：

- 口径 A：`Makefile.am`/`configure.ac` 声明的测试目标 → **0 个**；
- 口径 B：把 vendored lwIP 的 `START_TEST` 当测试 → **22 个**。

口径 B 不成立：那些用例既不被 `Makefile.am` 引用，也没有被 `configure` 探测的框架，
在本包里永远不会被编译或执行；把它们计入分母会得到「22 个用例 0 个通过」的假缺陷，
把它们计入分子又会变成不实的覆盖声明。因此本包按口径 A 申报 N = 0，并在此留档口径 B
的存在与排除理由，供审方复核。
