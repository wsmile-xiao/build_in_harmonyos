# quictls 3.3.0-quic1 适配笔记

## 编译环境
- 构建系统: custom（perl `./Configure` + make，大写字母 C，非 autotools）
- 编译日期: 2026-09-29
- 编译器: clang（OHOS SDK llvm，显式 `CC=clang`；Configure 默认选 gcc，环境无 gcc）
- 状态: built（CI upload 成功后升 published）

## 编译步骤

```bash
# configure（R33：CC 来自 recipe 常量，非裸 shell 变量）
perl ./Configure linux-aarch64 CC=clang \
    --with-rand-seed=getrandom no-asm no-shared \
    --prefix=$PKG --openssldir=$PKG/ssl
# 构建（-j2 对齐已合并 openssl/3.5.8.1；OOM 回退 -j1）
LD_LIBRARY_PATH=<OHOS SDK>/llvm/lib:<OHOS SDK>/llvm/sysroot/usr/lib:${LD_LIBRARY_PATH:-} \
    make build_sw -j2
# 安装（install_sw 跳 docs：3.3.x doc 生成缺 pod.in，make install 会失败）
make install_sw
```

关键参数说明：
- `--with-rand-seed=getrandom`：排除 DEVRANDOM_WAIT/FD_SET 路径（E235 在 3.3.0 的落点；
  实测 configdata 0 次 DEVRANDOM 出现，rand_unix.c 零补丁）
- `no-asm`：OHOS SDK 无预置 asm 目标（对齐 3.5.8.1）
- `no-shared`：R26 openssl 为系统同名库，静态构建避免 .so 污染 /lib
- LD_LIBRARY_PATH 注入：lld 链接 test/*.so 需 libxml2.so.16（位于 llvm/lib）
- **QUIC 特性：保持默认 boring-quic-api（不传 enable-quic）**——选型依据见下节

## QUIC 特性选型（本配方核心 delta）

quictls 3.3.0-quic1 fork 有两套**互斥**的 QUIC-TLS API（Configure L1221 硬闸：
"boring-quic-api and quic are incompatible options"）：

| 特性 | 默认 | API 形态 | 消费方 |
|------|------|---------|--------|
| boring-quic-api | 启用 | BoringSSL 兼容推模式：`SSL_set_quic_method` / `SSL_provide_quic_data` / `SSL_set_quic_transport_params` / `SSL_quic_read_level` 等 | msquic、lsquic 等外部 QUIC 栈 |
| quic（原生栈） | 禁用 | `OSSL_QUIC_client_method` + 内建 QUIC transport（engine/channel/stream） | 使用 OpenSSL 内建 QUIC 栈的应用 |

**决策：保持默认 boring-quic-api，不启用原生 quic。** 依据：
1. **生态信号**：libmsquic 2.5.7（已合并）vendored quictls configure = 裸
   `Configure linux-aarch64`（默认特性 = boring-quic-api）；lsquic 4.9.4
   （DRAFT-13533）消费同一 API 族（SSL_provide_quic_data 系）。
2. **原生栈上游缺陷**：`enable-quic no-boring-quic-api` 实测
   `70-test_quic_{tserver,multistream}` 2 套确定性失败——`quic_tls.c:768`
   `ossl_tls_add_custom_ext_intern`（quic_transport_parameters 扩展注册）失败
   → `RAISE_INTERNAL_ERROR`，固定种子全迭代复现，纯内存逻辑与平台无关
   = 3.3.0-quic1 原生栈上游缺陷（仓库 2025-04-10 归档，后继仓库 quictls/quictls）。
3. **boring-quic-api 模式的功能面验证**：由本配方 test_package 的
   test_quictls.c T8-T12 覆盖（QUIC-TLS provider API 逐项实测 PASS）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 带 `-D__MUSL__` 编译失败：`sockets.h:212: unknown type name 'ossl_inline'` | 从 3.5.x 移植的 FD_SET 有界实现依赖 `ossl_inline`；3.3.0 的 sockets.h 未包含 macro.h（3.5.x 中该头文件已引入） | 不加 `-D__MUSL__`（见 #2/#3） |
| 2 | 3.3.0 是否需要 FD_SET 有界补丁？ | 实测：rand-seed=getrandom 排除 DEVRANDOM 路径后，其余 FD_SET 使用（speed.c job 调度）在 OHOS SDK 上链接无虞（libcrypto/libssl + openssl CLI + 300+ 测试二进制全部产出，0 链接错误，make test 3185 项全跑） | 删除 2 个探索期补丁（0001 speed.c / 0002 sockets.h），conandata 不带 patches，补丁机制保留 no-op |
| 3 | 为何 3.5.8.1 的 `-D__MUSL__` + 有界补丁方案不适用 | E235 的 `__fd_chk` 问题集中在 DEVRANDOM 路径；3.3.0 中同一 flag 更彻底地排除该路径（configdata 0 次 DEVRANDOM） | 保留 `--with-rand-seed=getrandom` 为 E235 在 3.3.0 的等效手段；弃 `-D__MUSL__`（W0b 偏离，证据见 #1/#2） |
| 4 | 原生 quic 栈 2 套测试失败（tserver/multistream） | 上游 3.3.0-quic1 原生栈缺陷（quic_tls.c:768 扩展注册 INTERNAL_ERROR），与平台无关 | 不启用 quic 特性，采用 boring-quic-api（见选型节）；沉淀知识草稿 |
| 5 | lang-preflight 误判 `mixed (module-build)` | vendored `external/perl/Text-Template-1.56/Makefile.PL` 触发 Makefile.PL 检测 | 按仓库先例（exr_image/cmsis-dsp）记录证据后继续：C 主体 83%，任务语言 cpp 兼容 |

## 源码修改

无补丁。探索期曾直接修改 speed.c/sockets.h 两处（FD_SET 有界化），经 #1/#2
实证 3.3.0 不需要后移除；最终 conan-verify G2 以 0 补丁干净源码构建通过。

## 依赖版本

- 无 Conan 依赖（自包含加密/QUIC-TLS 库，`requirements()` 为空）
- perl：CI worker 真机自带（已合并的 openssl/3.5.8.1 同口径，不 tool_requires）

## 验证结果（R51 上游测试三步法）

**1. 清点**：上游测试套件 = `test/recipes/*.t` **312 文件 / 3185 tests**（prove）；
其中 QUIC 相关 `70-test_quic_*` 14 套（cfq/fc/fifd/lcidm/multistream/qlog/rcidm/
record/srtm/stream/txp/txpim/tserver/wire）。

**2. 实跑**（Option A = 交付配置，boring-quic-api 模式，2026-09-29 本机 OHOS aarch64）：

```
$ make test
Files=312, Tests=3185, 1311 wallclock secs ( 9.98 usr  4.55 sys + 51.57 cusr 49.60 csys = 115.70 CPU)
Result: PASS
```

- **Result: PASS（0 失败）**；文件级 68 skip
- skip 说明：`70-test_quic_*` 14 套按设计 skip（boring-quic-api 模式下 quic 特性
  禁用，测试自身 `disabled('quic')` 守卫触发 `skip_all: QUIC protocol is not
  supported by this OpenSSL build`）；其余 skip 为 engine/dynamic-feature 相关
  （与已合并 openssl/3.5.8.1 同口径）
- 对照（Option B `enable-quic`，仅选型评估用）：QUIC 14 套中 12 套通过、
  2 套确定性上游失败（tserver/multistream，见问题 #4）

**3. 回填**：
- 本配方 L1 测试 test_package/test_quictls.c：**14 项 PASS**（加密核心 7 项：
  version/SHA-256/AES-256-GCM/EC P-256/RAND/TLS1.3/X509；QUIC-TLS provider API 7 项：
  SSL_set_quic_method/SSL_is_quic/SSL_set_quic_transport_params/peer params/
  read_write_level/max_handshake_flight_len/process_quic_post_handshake 守卫语义）
- 3.3.0 API 签名差异（与 3.5.x 不同，测试中已按 3.3.0 签名适配）：
  `X509_set_subject_name` 2 参、`SSL_get_peer_quic_transport_params` 3 参、
  `EVP_EncryptInit_ex` 5 参（6 参为 `_ex2` 变体）
- conan-verify 8 道门禁全绿（G1/G2/G3/G4 + L2/L4/L5，2026-09-29），
  判定：可标记 published

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 配方（custom-perl 构建，零 requires，no-op 补丁机制） |
| conandata.yml | 官方 tag tarball URL + sha256（无 patches） |
| test_package/ | L1 测试（14 项，QUIC-TLS provider API 实质依赖） |
| commands.json（软件级） | openssl CLI 声明（R38） |

## 注意事项

- 超时预算：CI 默认 3600s 足够（实测 conan create 约 15 分钟，无需仓库条目）；
  `ci/config/build_timeouts.txt` 的 `quictls/3.3.0-quic1 7200` 为**本地 W3 配置**，
  非本 PR 提交内容（ci/ 不随软件 PR，W2/先例一致）
- 版本字符串 `OpenSSL 3.3.0+quic`（test_package T1 用于校验 fork 身份）
- 该 tag 的 GitHub release **无附件资产**（asset_count=0），源码用官方 tag
  tarball（R39 官方源；CI 自动加镜像 fallback）
- 若未来消费者需要原生 QUIC 栈（OSSL_QUIC API）：评估迁移后继仓库
  quictls/quictls（3.3.0-quic1 原生栈存在 2 套测试的上游缺陷，见知识草稿）
- 与 openssl/3.5.8.1 共存无冲突：包名不同（quictls vs openssl），下游按包名选择
---

**编译结束**: 2026-09-30 00:32
**最终状态**: built
