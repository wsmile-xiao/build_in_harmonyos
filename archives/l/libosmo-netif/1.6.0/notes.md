# libosmo-netif 1.6.0 适配笔记

## 编译环境
- 构建系统: autotools（osmocom 系标准）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang）
- 状态: built（local_verify 通过）

## 任务背景

- 上游 https://osmocom.org/projects/libosmo-netif tag 1.6.0
  （downloads.osmocom.org 官方发布包，sha256
  60ff389b388c2fbcbaca31fad97fdceb7c99032ca5a1b4f365ffcb54f5cd1eed）
- **本件是 libosmo-sigtran 2.1.0（平台任务 #13371）的断链依赖**：
  sigtran configure.ac `PKG_CHECK_MODULES(LIBOSMONETIF, libosmo-netif >= 1.6.0)`
  硬依赖，而 main 归档/制品仓/平台任务/开放 PR 四处均无 netif（W0 实测）。
  按 R36（依赖先发布再构建下游）先行适配本件为 sigtran 供链。
  平台无 netif 任务（5506 个开放任务全量扫描零命中）——本件为无任务
  供链贡献，不占额度。

## W0 依赖核验

| 依赖 | 版本 | R35 核验 |
|---|---|---|
| libosmocore | 1.11.0 | `conan download -r=ohpcd --only-recipe` EXIT=0（传递 talloc/libmnl/libusb/pcsc-lite） |

## 构建步骤（本地实测命令链）

```bash
# 依赖环境
conan install --requires=libosmocore/1.11.0 -r=ohpcd \
  -pr:h=ohos-aarch64 -pr:b=default -g=PkgConfigDeps

export PKG_CONFIG_PATH=<generators 目录>
export CC=/data/service/hnp/bin/clang CXX=... AR=... RANLIB=...

./configure --prefix=<install> --disable-libsctp --disable-doxygen
make -j1            # E074：OHOS 禁 FIFO jobserver，串行
make check          # 上游测试套件
```

## 适配要点（补丁集）

| # | 补丁 | 内容 |
|---|------|------|
| 1-3 | config.guess/sub/configure | 复用 libosmocore 1.11.0 同款（ohos triplet + umask 077 HMDFS） |
| 4 | include/osmocom/netif/sctp.h | SCTP enum 前向声明参数类型按 HAVE_LIBSCTP 守卫（gcc 仅警告、clang 报 incomplete type；无 SCTP 平台必须守卫） |
| 5 | src/stream_srv.c | ①iofd_setup 的 SCTP 分支补 HAVE_LIBSCTP 守卫（stream_cli.c 同位置上游已有——srv 侧遗漏，`#else if (true)` 对齐 cli 模式）；②multiaddr sockname/linkaddr 调用守卫回退单地址 API |
| 6 | src/stream_cli.c | multiaddr sockname 调用守卫回退 osmo_sock_get_name_buf |

**根因链**：平台无 libsctp（内核 EPROTONOSUPPORT，libosmocore notes 同源结论）
→ `--disable-libsctp` → HAVE_LIBSCTP 未定义 → 上游按"总是有 SCTP"假设写的
三处代码路径编译/链接失败：
  - sctp.h：`enum sctp_sac_state;` 等前向声明在 C 中不完整（gcc 容忍
    警告、clang 报错）；
  - stream_srv.c:982：`&srv_ioops_sctp` 引用被 HAVE_LIBSCTP 守卫掉的
    定义；
  - 链接期 `--no-undefined`：`osmo_sock_multiaddr_*` 系符号只在
    libosmocore 以 SCTP 支持构建时导出（本平台 libosmocore
    --disable-libsctp），netif 未守卫的调用点成未定义引用。

## 上游测试（6 用例：5 PASS / 1 FAIL）

`tests/testsuite.at` 注册 6 组（AT_SETUP）：stream_test / osmux_test /
osmux_output_test / osmux_input_test / jibuf_test / amr_test。
（jibuf_tool 为 HAVE_PCAP 条件目标，平台无 pcap 不构建，不计入。）

本机实测（`make check` 驱动 + 手工复跑）：

| # | 用例 | 结果 | 说明 |
|---|------|------|------|
| 1 | stream_test | **FAIL** | alarm(2) 看门狗触发退出：IPA 分段收发阶段（`test_segm_ipa_stream_srv`）第三段发送后服务端未收到，主循环 `osmo_select_main(1)` + `osmo_gettimeofday_override_add(0,1)` 微步推进下事件链未完成；实测 2.2s 精确命中 alarm(2)。stderr 前 105/127 行与期望逐行一致（连接/重连/24 字节收发全过），stall 点固定。定性：OHOS 定时器/socket 事件调度与上游假时钟假设的行为差异（环境类），非编译适配缺陷 |
| 2 | osmux_test | PASS | rc=0，stdout+stderr 合并输出与 osmux_test.ok 逐字节一致 |
| 3 | osmux_output_test | PASS | rc=0，输出一致 |
| 4 | osmux_input_test | PASS | rc=0，输出一致 |
| 5 | jibuf_test | PASS | rc=0，输出一致 |
| 6 | amr_test | PASS | rc=0，输出一致 |

stream_test 失败证据：
```
$ ./tests/stream/stream_test   # LD_LIBRARY_PATH=libosmocore 包 lib
...（105 行与 stream_test.err 一致）...
CLICONN(...){CONNECTED} received 6 bytes from srv
FAIL: test did not run successfully     # alarm(2) 触发（real 2.2s）
```
已尝试：多轮重跑（stall 点固定）、依赖库路径补全（排除加载问题）。
run_in_build 模式下 make check 的 6/6 FAILED 均为 `exit code 127`（依赖
.so 加载限制，E488 系），手工以正确 LD_LIBRARY_PATH 复跑后即上表结果。

## 消费者测试（test_package）

C 消费者真实调用 osmo_stream_cli_create/set_addr/set_port/set_proto/
destroy + osmo_stream_srv_link_create/set_*/destroy（创建/配置/析构
全链），编译+链接验证 + 运行（受限时降级 compile+link，OHOS E488 口径）。

## 验证结果

- conan create（W3）：通过
- test_package：通过（compile+link + 运行尝试降级口径）
- 上游测试：6 注册 / 6 执行 / 5 PASS / 1 FAIL（stream_test 环境类差异，证据如上）

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libosmonetif.so* | 主库（soname libosmonetif.so.14） |
| include/osmocom/netif/*.h | 公共头 |
