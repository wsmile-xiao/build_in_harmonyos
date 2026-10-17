# rlog

rlog（RLog）是 Valient Gough 编写的 C++ 消息日志库：以「通道（channel）+ 节点
（node）」组成发布/订阅网络，支持日志级别、层级通道过滤、`rAssert` 断言抛错与
计时 API。上游为 autotools 项目，本次适配版本 1.4（2008-06 发布）。

- **来源**: https://distfiles.macports.org/rlog/rlog-1.4.tar.gz
- **许可证**: LGPL-2.1-or-later（归档内 COPYING 为 LGPL v2.1 全文；源码头声明
  "either version 2.1 of the License, or (at your option) any later version"）
- **分类**: library / 日志

## 源码来源说明

上游原站 `arg0.net`（作者个人域名，现指向 Google Sites 个人站点）上的 rlog 页面与
tarball 均已 404，`rlog.sourceforge.net` 项目页同样失效，且不存在官方 GitHub 仓库。
本仓取 MacPorts distfiles 保存的原始 tarball：

- `rlog-1.4.tar.gz`，640641 字节，sha256 `a938eeedeb4d56f1343dc5561bc09ae70b24e8f70d07a6f8d4b6eed32e783f79`
- 与 Debian pool 的 `rlog_1.4.orig.tar.gz` **字节一致**（两个权威分发点互证），
  归档顶层目录 `rlog-1.4/`，142 个成员

## 软件描述

库的核心对象是 `RLogChannel`（通道，可按 `a/b/c` 层级组织）与 `RLogNode`
（发布/订阅节点）；`StdioNode`/`SyslogNode` 是内置输出节点。日志宏
`rDebug`/`rWarning`/`rError`/`rLog(channel, fmt, ...)` 经发布链路把格式化消息投递给
订阅了相应通道的节点；`rAssert`/`rAssertSilent` 失败时抛出携带
`file()/line()/function()/component()` 的 `rlog::Error`。

## 适配说明

- **构建系统**: autotools（上游 tarball 自带 configure，未使用 autoreconf）
- **交叉编译**: 显式 `--build/--host=aarch64-unknown-linux-gnu`（自带 config.sub
  实测接受该三元组；补丁 0001 只修 config.guess 对 HarmonyOS 的识别）
- **平台补丁**: 0001（config.guess 识别 HarmonyOS）、0002（HMDFS 下 config.status
  临时目录改 umask 022 + mkdir；C++ 候选表加入 clang++）、0003（VPATH 构建下 docs
  安装改用 `$(top_srcdir)`/`$(srcdir)` 路径）
- **并行构建**: `make -j1`（HMDFS 不允许 mkfifo，无法建 jobserver fifo）
- **库类型**: 非系统同名库（OHOS 系统与 sysroot 无 librlog），默认 `shared=True`
- **消费者**: conan 生成的 `rlog::rlog` CMake target；`-lpthread` 经
  `cpp_info.system_libs` 传递

## 测试

| 类别 | 数量 | 结果 |
|------|------|------|
| 上游注册测试（`make check`） | 0（无 TESTS 注册） | — |
| 上游 noinst 程序（test / testlog） | 2 | 2/2 PASS（exit 0，build() 内实跑） |
| 消费者测试断言（test_package/test.cpp） | 11 | 11/11 PASS |

上游只把 `test`、`testlog` 声明为 `noinst_PROGRAMS`（`rlog/Makefile.am`），
没有 `TESTS` 变量，因此 `make check` 不做任何事；两者随构建编译并由 build()
显式运行，作为上游功能证据。

## 版本列表

| 版本 | 状态 | 适配日期 | 备注 |
|------|------|----------|------|
| 1.4 | built | 2026-09-18 | 上游最后一个发行版本；共享库 + 头文件 + pkg-config + 上游文档 |
