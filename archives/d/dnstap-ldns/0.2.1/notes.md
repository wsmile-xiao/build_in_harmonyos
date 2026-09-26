# dnstap-ldns 0.2.1 — 适配笔记

## 概述

dnstap-ldns 是 dnstap 编码 DNS 流量的解码参考工具（CLI，Apache-2.0）。
本适配面向 HarmonyOS PC（aarch64, OHOS 6.0, clang 15），Conan 2.29.1 + Autotools。

## 构建入口

- 上游：https://github.com/dnstap/dnstap-ldns ，tag v0.2.1
- 源码：configure.ac + Makefile.am（autotools），无提交的 configure（GitHub archive 需 autoreconf）
- 产物：单可执行文件 `dnstap-ldns`（链接 ldns/fstrm/protobuf-c，全部静态）
- 依赖：ldns/1.9.0、libfstrm/0.6.1、protobuf-c/1.5.1（ohpcd 均已发布，W0 通过）

## OHOS 适配要点

1. **autoreconf 自举**：tag archive 无 configure；`tool_requires automake/1.18 + libtool/2.5.4`，
   autoconf 2.72 由系统提供（与 libfstrm 0.6.1 同路径）。
2. **protoc-c 预生成绑定**：ohpcd 的 protobuf-c/1.5.1 制品 `package()` 剥离 bin/，
   构建期无 protoc-c 工具可用。因此作者期用同一 protobuf-c 1.5.1 的 `protoc-gen-c` 插件
   （protoc 3.17.3 驱动，`--c_out`）从官方 `dnstap.pb/dnstap.proto` 预生成
   `dnstap.pb-c.c/.h`（本目录 `generated/`），并 patch：
   - configure.ac：删除 `AC_PATH_PROG(protoc-c)` 硬检查，`PROTOC_C` 替换为 `true`；
   - Makefile.am：移除 `.proto.pb-c.c/.pb-c.h` 后缀规则与 BUILT_SOURCES 重生成依赖，
     直接编译预生成源文件。
3. **pkg-config 模块名修正**：ohpcd ldns/1.9.0 制品的模块名是 `ldns`（ldns.pc），
   上游 configure.ac 写 `PKG_CHECK_MODULES([libldns],[libldns])` 会失败，
   patch 为 `PKG_CHECK_MODULES([libldns],[ldns])`（变量前缀不变，Makefile 的
   `${libldns_CFLAGS}`/`${libldns_LIBS}` 不受影响）。libfstrm / libprotobuf-c 模块名与
   ohpcd 制品一致（libfstrm.pc / libprotobuf-c.pc），无需修正。
4. **E011/E114（config.status 临时目录）**：autoreconf 生成的 configure 用
   `umask 077 && mktemp -d` 建临时目录，HMDFS 上不可写 → build() 中把 `umask 077`
   替换为 `umask 022`（libfstrm 0.6.1 / ldns 1.9.0 同款修复），configure 通过。
5. **E074（make 并行）**：`make -j2` 报 `jobserver mkfifo: Operation not permitted`，
   改 `-j1`。
6. **config.guess**：无法识别 HarmonyOS，显式传 `--build/--host=aarch64-unknown-linux-ohos`。

## 测试

- 上游无自动化测试：Makefile.am 无 TESTS，`make check` 无此目标（实测 "No rule to make target 'check'"）。
  source_declared_total = 0（官方 tag 0.2.1 无任何测试声明）。
- 消费者用例（test_package，真实运行）：`dnstap-ldns -x` 解码手工构造的合法
  dnstap protobuf（Dnstap{type=MESSAGE, message={AUTH_QUERY, INET, UDP,
  127.0.0.1, 53/53}}，hex `7801721008011001180122047f00000130353835`）：
  quiet 输出含 `AQ 127.0.0.1 UDP`，YAML 输出含 `AUTH_QUERY/127.0.0.1/UDP`，
  退出码 0。这是唯一且真实的运行用例，同时作为消费者验证。

## 验证结论

- `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`：通过
  （build + install + test_package 全绿）。
- 产物：`bin/dnstap-ldns`（OHOS armv8，静态链接三库）。
- R38：CLI 工具，软件级 `commands.json` 已声明（name=dnstap-ldns, type=tool）。

## 基线隔离复验记录（其他库文件）

`archives/l/libXext/` 大小写双路径（`libXext/` 与 `libxext/`）在本 worktree 创建时
出现与 HEAD 不一致的预存内容污染（README.md/manifest.yaml）。处理：
- 记录污染内容 SHA-256（pre）：README `26bd9228...`，manifest `f85a944d...`
- `git checkout HEAD -- <路径>` 恢复为 HEAD 内容（post SHA == HEAD blob）：
  README `69afd687de50b246ec2011eba133854124176707b85e1c92e6864c3d42849fb4`，
  manifest `863136da5ccbc16d9aac2cd5a8595fb33b37e8b741a0fef65cfc7637dd593c89`
- 对 `archives/l/libxext/README.md` 与 `manifest.yaml` 设置 skip-worktree（与主
  worktree 既有标记一致），确保不会进入本库 staged/commit/PR
- 当前库 diff/staged/PR 均不包含 libXext/libxext 任何路径
---

**编译结束**: 2026-09-26 07:07
**最终状态**: built
