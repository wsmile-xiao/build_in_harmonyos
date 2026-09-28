# libosmo-sccp 1.9.0 适配笔记

## 编译环境
- 构建系统: autotools（osmocom 系标准）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang）
- 状态: published

## 任务背景

- 上游 https://osmocom.org/projects/libosmo-sccp tag 1.9.0
  （downloads.osmocom.org 官方发布包，sha256
  b6c219e57c79bda9eb0edb7eae64ba01b952126ecb48b6a6667e4fce21f977a9）
- 依赖链：libosmocore/1.11.0（含 libosmovty/libosmogsm）+ libosmo-netif/1.6.0
  均已发布（W0 conan download EXIT=0）。

## W0 依赖核验

| 依赖 | 版本 | R35 核验 |
|---|---|---|
| libosmocore | 1.11.0 | `conan download -r=ohpcd --only-recipe` EXIT=0（传递 talloc/libmnl/libusb/pcsc-lite） |
| libosmo-netif | 1.6.0 | `conan download -r=ohpcd --only-recipe` EXIT=0 |

## 构建步骤（本地实测命令链）

```bash
conan install --requires=libosmocore/1.11.0 --requires=libosmo-netif/1.6.0 \
  -r=ohpcd -pr:h=ohos-aarch64 -g=PkgConfigDeps -of=<generators dir>
export PKG_CONFIG_PATH=<generators dir>
export CC=/data/service/hnp/bin/clang
./configure --prefix=<install> --disable-libsctp --disable-doxygen
make -j1            # E074：OHOS 禁 FIFO jobserver，串行
make -j1 check      # 上游测试套件：5/5 通过
make install DESTDIR=<test-prefix>
```

> 注意：configure.ac 被补丁修改后（sctp 可选），须 touch 全部 Makefile.in/
> aclocal.m4 使其不旧于 configure.ac，否则 make 会用 missing 调 automake-1.16
> 重建（本机无 automake-1.16）。

## 适配要点（补丁集）

| # | 补丁 | 内容 |
|---|------|------|
| 1-3 | config.guess/config.sub/configure | 复用 libosmocore 1.11.0 同款（ohos triplet + umask 077 HMDFS） |
| 4 | configure.ac（+生成的 configure 同步） | 新增 `--disable-libsctp`；`AC_SEARCH_LIBS(sctp_recvmsg)` 硬失败降级为警告 |
| 5 | src/osmo_ss7.c | ①netinet/sctp.h、netif/sctp.h include 按 HAVE_LIBSCTP 守卫；②文件尾按 `!HAVE_LIBSCTP` 提供 osmo_sock_multiaddr_* 单地址回退实现 |
| 6 | src/osmo_ss7_asp.c | SCTP 专属代码按 HAVE_LIBSCTP 守卫：setsockopt 主地址簇、SCTP 通知处理/log_sctp_notification、xUA SRV/CLNT 通知分发块、connect_cb 的 apply-primary 调用点 |
| 7 | src/osmo_ss7_asp_peer.c | netinet/sctp.h include 守卫 |
| 8 | src/osmo_ss7_vty.c | ①顶部 define `_GNU_SOURCE`（OHOS netinet/tcp.h 仅在此宏下定义 struct tcp_info）；②SCTP apply-primary 调用点及局部变量按 HAVE_LIBSCTP 守卫 |
| 9 | src/osmo_ss7_xua_srv.c | sctp includes 守卫 + apply-primary 调用点守卫 |

**根因链**：平台无 libsctp 且内核不支持 SCTP（EPROTONOSUPPORT，libosmocore/
netif 同源结论）→ `--disable-libsctp` → HAVE_LIBSCTP 未定义。libosmo-sccp 1.9.0
上游把 SCTP 当作"总有"（configure.ac 硬 AC_SEARCH_LIBS、5 个源文件无条件
`#include <netinet/sctp.h>` / `<osmocom/netif/sctp.h>`），且 libosmocore
(--disable-libsctp) 不导出 `osmo_sock_multiaddr_*` 系列符号。

三个附加平台问题：
1. `osmo_sock_multiaddr_*`（libosmocore 无 SCTP 时不存在）→ 在 osmo_ss7.c 按
   `!HAVE_LIBSCTP` 提供回退：get_ip_and_port 回退单地址 API、snprintf 纯格式化、
   SCTP-only 多宿主 add/del 视为成功 no-op（单宿主 socket 绑定地址集已在
   bind/connect 时固定）。
2. `struct tcp_info` 不完整类型 → `_GNU_SOURCE`（vty.c 顶部）。
3. 生成文件时间戳 → 修改 configure.ac 后 make 触发 automake 重建，touch 生成文件。

## 上游测试（5 用例全部通过）

`tests/testsuite.at` 注册 5 组（AT_SETUP）：m2ua / mtp / sccp / xua / ss7。
（tests/vty/ 为外部 VTY 测试，需 --enable-external-tests 且 osmo-python-tests，
上游默认不启用，不纳入 make check。）

本机实测 `make check`：**All 5 tests were successful**，逐条：

| # | 用例 | 结果 | 说明 |
|---|------|------|------|
| 1 | m2ua | PASS | m2ua_test rc=0，输出与 m2ua_test.ok 一致 |
| 2 | mtp | PASS | mtp_parse_test rc=0，输出与 mtp_parse_test.ok 一致 |
| 3 | sccp | PASS | sccp_test rc=0，输出与 sccp_test.ok 一致 |
| 4 | xua | PASS | xua_test rc=0，stdout/stderr 与 .ok/.err 一致 |
| 5 | ss7 | PASS | ss7_test rc=0，输出与 ss7_test.ok 一致 |

`make distcheck`：失败于 `dist-gzip`——本平台 gzip 不支持 `--best` 选项
（`gzip: Unknown option 'best'`，工具链差异），非测试失败；上游测试以
`make check` 全量通过为准。

## 消费者测试（test_package）

C 消费者（test_sccp.c）真实调用 libosmo-sigtran 公开 API：SS7 实例创建/查询
（osmo_ss7_instance_find_or_create/find）、ASP 创建与 proto/trans_proto 取值
（osmo_ss7_asp_find_or_create2/get_proto/get_trans_proto）、AS 创建与 ASP 关联
（osmo_ss7_as_find_or_create/add_asp/del_asp）、全链析构。编译+链接+运行全通过。

## 验证结果

- conan create（W3）：通过
- test_package：通过（compile+link + 运行）
- 上游测试：5 注册 / 5 执行 / 5 PASS / 0 FAIL / 0 SKIP，通过率 100%

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libosmo-sigtran.so* | 主库（soname libosmo-sigtran.so.10） |
| lib/libsccp.a / libmtp.a / libxua.a | legacy 静态库 |
| bin/osmo-stp | 信号转接点可执行 |
| include/osmocom/{sccp,sigtran,mtp}/*.h | 公共头 |
| etc/osmocom/osmo-stp.cfg | 示例配置 |

## 注意事项

- R38：包含 osmo-stp 可执行 → 软件级 commands.json 已生成
  （archives/l/libosmo-sccp/commands.json）。
- conanfile.py `generate()` 注入 `-fno-emulated-tls`（原生 TLS），与
  libosmocore/libosmo-netif 跨 DSO TLS 模型统一。
- legacy 静态库（sccp/mtp/xua）上游仅以静态形式提供，shared 模式下也不移除。
---

**编译结束**: 2026-09-27 13:15
**最终状态**: published
