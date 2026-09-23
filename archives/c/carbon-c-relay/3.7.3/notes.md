# carbon-c-relay 3.7.3 适配笔记

## 任务与上游
- 任务号: #6200（activity: 开源鸿蒙PC专项积分赛；claimer: wanderlust_0823；changeType: feat）
- 分支: feat/carbon-c-relay-3.7.3
- 上游仓库: https://github.com/grobian/carbon-c-relay
- 上游版本: v3.7.3（tag tarball）
- 源 URL: https://github.com/grobian/carbon-c-relay/archive/refs/tags/v3.7.3.tar.gz
- SHA256: 86a98bfb33a3f2f9ee48dac7f99aa19f21c0a5972a0fff5db376deaef8f95f54
- 语言: C（94%；任务平台声明 cpp，c↔cpp 兼容族，lang-preflight 通过：detected=c, build_system=autotools）
- 构建系统: autotools（release tarball 自带 configure 与 bison/flex 生成文件）
- 依赖: 无 conan 依赖。gzip 走 OHOS sysroot 自带 zlib（configure 实测 zlib.h/-lz 可用）；
  openssl/lz4/snappy/oniguruma/pcre 头文件在 sysroot 不可得，configure 自动禁用对应特性。

## 适配方式（补丁全部为平台适配，不改业务/测试语义）
1. config.guess + config.sub 升级至 GNU 2024-07-27 版（取自本机 opendmarc-1.4.2
   构建残留的 automake 支持文件）：旧版无法识别 `HarmonyOS` uname
   （unable to guess）也不接受 `aarch64-unknown-linux-ohos`（config.sub
   "OS 'ohos' not recognized"）。E007。
2. configure 移除两处 `(umask 077 && ...)` 包裹：HMDFS 权限组合下 mktemp -d
   创建的临时目录内写 dummy.c 报 Permission denied（E011/E114）。保留真实
   临时目录创建逻辑。
3. issues/issue267.conf 与 test/issue267.out：metrics 日志路径
   /tmp/carbon-c-relay-metrics.log → carbon-c-relay-metrics.log（E002：
   OHOS /tmp 只读）。该测试验证 cluster log-file/next-hop 配置解析语义，
   路径本身非测试目标；conf 与 .out 期望回显同步修改，测试由失败转通过。
4. configure 额外传入 cache 变量 ac_cv_func_malloc_0_nonnull=yes /
   ac_cv_func_realloc_0_nonnull=yes：名义交叉（--host=ohos 与 --build=gnu
   不同）下 AC_FUNC_MALLOC/REALLOC 的运行探针按失败处理，会把 malloc
   定义为不存在的 rpl_malloc 导致 relay.c 编译失败（clang 报 incompatible
   integer to pointer conversion）。实际为同架构真机构建，musl/glibc 语义
   均满足，用 cache 变量如实声明（无源码修改）。

## W0/W0b
- ci/scripts/preflight_check.sh carbon-c-relay/3.7.3：通过（无 conanfile 阶段无依赖可查；
  配方零依赖，R36 无涉及）
- lang-preflight：通过（task=cpp, detected=c, 源码主体 c:17/94%, build_system=autotools）

## 上游测试（R51 四数口径）
- 上游静态声明总数: 38（Makefile.am CRTESTS 全量；SSL 条件追加的
  dual-ssl/large-ssl/dual-large-ssl 因构建禁用 ssl 不计入，对应特性变体
  由运行器按 relay -v 特性探测条件跳过，属上游设计）
- 实际执行: 38；通过: 29；失败: 9；跳过: 0
- 执行证据: ~/tmp/uc2/carbon-c-relay/make-check-final.log（设备侧）
  （Ran 38 tests with 9 failing；逐项 PASS/FAIL 输出齐全）
- 9 项失败逐项定性（第一条真实错误均已取证）：
  basic.stst / metriclimits.stst / buftest.gz.stst / large.stst / dual-udp.stst /
  dual-tcp.stst / dual-gzip.stst / large-gzip.stst / dual-large-gzip.stst
  全部为同一平台限制：`(ERR) failed to bind for .../sock.3020:
  Operation not permitted`——relay 配置中的 unix socket 监听在 OHOS 执行
  环境 bind 被拒（HMDFS ~/tmp 与 /data/local/tmp 两处实测均为 bind 拒绝，
  纯 TCP/UDP 监听与转发正常：server-type、buftest、dual-lz4、large-lz4 等
  非 unix-socket 服务器测试全部通过）。属平台策略限制，无法在当前执行
  环境内修复；不删测试、不改测试语义，如实申报。
- 上游测试修改说明：见上"适配方式"1-3；无测试删除，无断言弱化，
  issue267 修改后由失败转为通过。

## 消费者测试（test_package，1 项）
- test.sh 驱动打包出的 relay 真实执行：`-v` 版本横幅断言（carbon-c-relay
  v3.7.3）+ configtest 真实解析一份 cluster forward 配置（断言退出码 0、
  "parsed configuration follows" 与配置回显内容）。

## W3 本地验证
- conan create：见 conan-verify 日志（零依赖，本地可完整构建）
- 已知限制：unix socket 监听类功能在本平台执行环境不可用（见上），
  relay 的 TCP/UDP 转发、聚合、重写、configtest 功能正常。
---

**编译结束**: 2026-09-06 03:19
**最终状态**: built
