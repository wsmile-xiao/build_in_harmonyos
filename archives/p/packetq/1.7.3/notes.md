# packetq 1.7.3 适配笔记

## 选型与版本核验（2026-09-05）

本轮筛选吸取 plutosvg 1.3.3 / miniupnpc 2.3.11 两个版本错位任务的教训，
把**上游版本存在性**作为认领前硬闸：

- codeberg.org/DNS-OARC/PacketQ tags 实拉：`v1.7.3` 存在且为最新 release ✓
- homebrew formula stable 1.7.3 交叉印证 ✓
- 官方 dist 包 `https://www.dns-oarc.net/files/packetq/packetq-1.7.3.tar.gz`
  可下载（R39 官方源）✓
- 档案（含异名变体匹配）无 packetq；制品仓 `conan list packetq/1.7.3`
  零发布（R35）✓
- 平台任务 contrib-5880 仍在池 ✓

## 编译环境

- 构建系统: autotools（官方 dist 自带预生成 configure——设备实测无
  automake/libtoolize，dist 包正好绕开 autoreconf）
- 目标平台: HarmonyOS PC arm64（OHOS/aarch64 原生）
- 编译器: /data/service/hnp/bin/clang 15.0.4
- Conan: 2.29.1（OHOS 适配版），profile ci/conan/profiles/ohos-aarch64
- 状态: adapting（设备验证后更新）

## W0 依赖预检（2026-09-05，Mac 侧 conan 2.32 匿名直连 ohpcd）

- `conan download zlib/1.3.1 -r=ohpcd`（含二进制）→ package revision
  7ec24a23f2d13bf0a3658deb250d2777 下载成功 ✓
- zlib 为上游金标测试事实必需（test1-8.sh 直接读 pcap/*.pcap.gz，
  HAVE_LIBZ 决定 gz 支持）
- maxminddb：上游可选特性（PKG_CHECK 失败静默关闭），不引入（R1）

## R51 上游测试清点（官方 dist 实测）

- **有真实测试套件**：src/test/test1.sh ~ test8.sh（automake TESTS 注册），
  POSIX sh + `diff -uw` 金标对比；fixture：dns.pcap、dns6.pcap、
  ../../pcap/sample.pcap.gz
- 覆盖面：SQL 引擎全函数（聚合/字符串/if/truncate/netmask/name/位运算/
  like/having）、-j JSON 输出、-c CSV 输出、双栈 pcap
- 结论：`make check` 即为实质验证，recipe 在 build() 内嵌执行，金标失败 =
  构建失败

## 配方设计决策

| 决策 | 理由 |
|---|---|
| 显式三元组 --build/--host | packetq 的 2024 版 config.sub 连显式 ohos host 都拒绝（设备实测 "OS ohos not recognized"），改用 config.sub 认识且 build≠host 的对：--build=aarch64-unknown-linux-musl --host=aarch64-unknown-linux-gnu，交叉模式保留、config.guess 不执行 |
| umask 077→022 再生成 | packetq configure 恰含 2 处 `umask 077`（与 libxrandr 契约一致），OHOS 下防止 DESTDIR 产物权限 600 |
| requires zlib/1.3.1 | 金标测试读 .gz fixture；二进制已发布实证 |
| build() 内嵌 `make check` | 上游 8 项金标是最强实质验证（R34/R51），失败即 G2 失败 |
| test_package 实跑安装后的工具 | R38 工具类包：消费者层验证 bin/packetq + 金标行数（[8]）+ qname 聚合（www.se.），金标用 brew packetq 1.7.3 在 macOS 实跑取得，pcap 解析确定性与平台无关 |
| 剥离 libxrandr 的 linker-view/pc 手术 | 工具包无依赖库链接、无 .la/pc 元数据，不需要 |

## 待办（Phase 2，设备侧）

- [x] mailbox 通道可用（plutosvg 会话已验证，origin/main 已更新至 29f362376 前基线）
- [x] init-build → 手动 configure/make/**make check 8/8 金标** → conan-verify 八门禁 → finish（EXIT_CODE 0）

## Phase 2 构建记录（2026-09-05，mailbox 通道）

1. 手动构建：configure（修正三元组 musl/gnu 对）→ make → **make check 8/8 PASS**
2. conan-verify 修复循环（3 轮，均非源码问题）：
   - #1: 起草时漏写 `_run_ohos` 方法 → AttributeError
   - #2: test_package 找不到 bin/packetq → autotools 默认 prefix=/usr/local 与
     DESTDIR 叠加嵌套；改 `--prefix=/` 直落包根
   - #3: PASS（G0/G1/G2/G3 + L2/L4/L5）
3. test_package 运行时输出曾误入档案树（JC4 口径），改写系统临时目录并清理
4. W3 本地 CI 通过；finish EXIT_CODE=0（EXIT_REASON: finish_success），状态 built

## 三元组修正细节（重要经验）

packetq dist 的 GNU config 是 2024 版：config.sub **连显式传入的
`aarch64-linux-ohos` host 都拒绝**（"OS ohos not recognized"）——这与
libxrandr 的 2026 版 config.sub（原生认识 ohos）不同。修正为 config.sub
均认识且 build≠host 的对：`--build=aarch64-unknown-linux-musl
--host=aarch64-unknown-linux-gnu`。交叉模式（跳过 conftest 执行）与
config.guess 不执行两点都保住。
---

**编译结束**: 2026-09-05 18:15
**最终状态**: built
