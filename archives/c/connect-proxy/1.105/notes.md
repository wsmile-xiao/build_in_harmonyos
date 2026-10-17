# connect-proxy 1.105 适配笔记（HarmonyOS PC · 裸 Makefile）

## 定位
- 产出 CLI 工具 bin/connect-proxy（按 Debian/Termux 命名惯例，由 package() 从上游 connect 更名）。
- 配方以已合入的 connect/1.106 配方为底稿（同一上游 gotoh/ssh-connect 的 1.106 版），差异：
  包名/版本、二进制更名、补丁 0001 的 musl 守卫去掉 `__OHOS__`、增加 ELF 自签。

## 源
- https://github.com/gotoh/ssh-connect/archive/refs/tags/1.105.tar.gz
- sha256: 96c50fefe7ecf015cf64ba6cec9e421ffd3b18fef809f59961ef9229df528f3e

## W0/W0b
- preflight_check.sh：无依赖声明，通过。
- 历史归档 archives/c/connect/1.106（notes.md + 配方 + 2 个可移植性补丁）已读，结论全部继承；
  两个补丁对 1.105 源码 `patch -p1 --dry-run` 直接干净适用。
- lang-preflight：task=cpp，detected=c（c↔cpp 兼容族），单文件 connect.c，通过。

## 探索构建（真机 builds/connect-proxy-1.105.work）
1. 裸 Makefile：`make CC=clang CFLAGS="-O2 -fPIE -D_GNU_SOURCE -DSOCKLEN_T=socklen_t" LDFLAGS="-pie -Wl,-z,relro,-z,now" LDLIBS=""`（R33， musl 内置 resolver 故清空 LDLIBS）。
2. 补丁 0001/0002 打入后编译零告警通过；`./connect -V` 输出 "Version 1.105"（未签名即可执行，签名后复测一致）。
3. 直连冒烟：`./connect -n 127.0.0.1 22` 得 errno=111（本机无 sshd），程序自身工作正常；
   完整中继行为由 test_package 的进程内 TCP/HTTP 代理/SOCKS5 服务端验证。
4. 补丁 0001 相对 1.106 版唯一改动：守卫 `#if defined(__OHOS__) || (defined(__linux__) && !defined(__GLIBC__))`
   收敛为 `#if defined(__linux__) && !defined(__GLIBC__)` —— OHOS clang 目标三元组含 linux 且 musl 无
   `__GLIBC__`，条件在 OHOS 上等价成立，同时不引入平台宏（R8/PF5）。

## 上游测试账本（R51）
- 上游无自动化测试：Makefile 仅 all/clean/veryclean/rebuild，无 check/test 目标；
  源码树仅 connect.c / Makefile / doc/ / make.bat / relay.el，无任何测试源文件（清点证据）。
  N_static = 0，N_executed = 0（如实申报，不虚构上游测试）。
- 消费者测试（test_package）4 用例 / 6 断言：驱动真实 connect-proxy 二进制——
  ① -V 版本横幅含 "Version 1.105"；② -n 直连 stdio<->TCP 双向中继；
  ③ -H HTTP CONNECT 隧道握手 + 数据中继；④ -5 -S SOCKS5 握手（ATYP=3 远端解析）+ 数据中继。

## 状态
built —— conan create 真机验证通过后回填（见 .ci-result.json / reports/）。
---

**编译结束**: 2026-09-09 00:10
**最终状态**: built
