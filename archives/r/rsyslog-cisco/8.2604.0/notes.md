# rsyslog-cisco 8.2604.0 适配笔记

## 编译环境
- 构建系统: autotools（上游经典 `./configure` + `make` 体系）
- 编译日期: 2026-09-27
- 编译器: clang / clang++（OHOS SDK 26.0.0.18, clang 15）
- CI 同款 profile: `ci/conan/profiles/ohos-aarch64`（`os=OHOS 6.0 / arch=armv8 / clang 15 / libc++`）
- 状态: built

## 打包范围
官方全量源码包，**仅编译打包两个 Cisco parser 模块**：

| 模块 | 源码目录 | 产物 |
|------|---------|------|
| `pmciscoios` | `plugins/pmciscoios/` | `lib/rsyslog/pmciscoios.so`（76096 B） |
| `pmcisconames` | `contrib/pmcisconames/` | `lib/rsyslog/pmcisconames.so`（80192 B） |

两模块均为 `MODULE_TYPE_PARSER` + `MODULE_TYPE_NOKEEP` 运行时插件，由 `rsyslogd`
通过 `loadmodule` 动态加载；本包不依赖 rsyslog 本体包，`cpp_info.libs` 为空。

## 编译步骤

```bash
# 1) 取源码（官方源 + Yocto 镜像 fallback，sha256 校验）
#    sha256 2a04b1cd6f0a5e2b60eec231acce3cf9927c4ed02bc5fbbe5dc4c35fcf887b64
# 2) 打 3 个 OHOS 适配补丁（config.guess / config.sub / configure）
# 3) configure（CI profile 注入 CONFIG_SHELL/SHELL = hnp bash）
./configure --prefix="$DEFAULT_PREFIX" --enable-pmciscoios --enable-pmcisconames
# 4) 只编目标模块；模块链接显式清空 $(LIBS)，避免带入无关 DT_NEEDED
make -C plugins/pmciscoios -j1 LIBS=
make -C contrib/pmcisconames -j1 LIBS=
# 5) 安装到包的 lib/rsyslog
make -C plugins/pmciscoios install DESTDIR="$TEST_PREFIX"
make -C contrib/pmcisconames install DESTDIR="$TEST_PREFIX"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 报 `cannot guess build type` | 上游 `config.guess`（2022 版）不识别 `uname -s` = `HarmonyOS` | 补丁 0001 → 输出 `aarch64-unknown-linux-ohos`（E007） |
| 2 | `--host=aarch64-linux-ohos` 被 `config.sub` 拒绝 | `config.sub` 未收录 `linux-ohos` 组合 | 补丁 0002（E007 配套） |
| 3 | `configure` 临时目录块失败/目录不可写 | `umask 077 && mktemp -d` 在 HMDFS 组权限语义下不可写 | 补丁 0003 → `umask 000`（E011） |
| 4 | 模块 `.so` 出现 `DT_NEEDED libz.so` | autotools 变量继承：`$(LIBS)` 携带 configure 探测到的 `-lz` | 仅对模块目标显式传 `LIBS=`，产物 `DT_NEEDED` 只剩 `libc.so` |
| 5 | 官方源下载被截断（`www.rsyslog.com` 不返回 Content-Length） | 传输层截断，非 sha 不匹配 | conandata 双 URL（官方 + Yocto 镜像，字节一致）+ conan 自动 fallback；本地 W3 预置 `.build-cache/predl_cache` |
| 6 | 消费者 E2E 链接期 `dlopen(RTLD_NOW)` 解析失败 | 测试桩未以 core 真名导出符号 | 桩按 core 真名导出（`Debug`/`MsgSetTAG`/`MsgSetHOSTNAME`/`MsgSetMSGoffs`/`setProtocolVersion`/`loadConf`/`r_dbgprintf`），并加 `-Wl,--export-dynamic`（R9 安全弹窗先触发再测试） |
| 7 | 模块内部 `DBGPRINTF` 日志不出现 | 桩未启用 `Debug` 门控变量 | 桩设 `int Debug = 1;`，模块日志经桩回调收集后可断言 |
| 8 | `parse2` 对合法 Cisco IOS 报文返回 `-2160`（`RS_RET_COULD_NOT_PARSE`） | 游标偏差：`ParseTIMESTAMP3164` 成功路径消费 **17 字节**（15 字符时间戳 + `": "`），原按 18 起步越过 TAG 首字符 `'%'` | 游标订正为 17 → `p2parse` 指向 TAG `'%'`，`parse2` 走通成功路径 |
| 9 | `GetParserName` 调用即 SIGSEGV（`rc=139`） | ABI 形状误判：真实签名带出参 `GetParserName(uchar **ppSz)`，原按 `void` 调用 | 按带出参 ABI 调用（`BEGINnewParserInst`/`ENDnewParserInst` 写回 `instanceConf_t **`） |

## 源码修改

3 个补丁（`patches/`，与 `conandata.yml` 顺序一致；干净树全量打入 3/3、`.rej` 0、`.orig` 0）：

| 补丁 | 目标文件 | 内容 |
|------|---------|------|
| `0001-config.guess.patch` | `config.guess` | 新增 HarmonyOS 识别分支 → `aarch64-unknown-linux-ohos`（+10/-0） |
| `0002-config.sub.patch` | `config.sub` | 接受 `linux-ohos` 内核-OS 组合（+2/-2） |
| `0003-configure.patch` | `configure` | 临时目录块 `umask 077` → `umask 000`（+2/-2，HMDFS 组权限语义） |

## 依赖版本

制品仓（ohpcd）预编译依赖，`conan download --only-recipe` 探测均在册：

| 依赖 | 版本 |
|------|------|
| `libestr` | 0.1.11 |
| `libfastjson` | 1.2609.0 |
| `zlib` | 1.3.1.1 |

## 验证结果

```bash
# conan create（CI 同款 profile）
✅ G1 配方完整性 PASS / G2 conan create PASS / G3 系统同名库隔离 PASS / G4 产物完整性 PASS
# W3 本地 CI 模拟（setup.sh + build_and_test.sh）
JC 检查模式: incremental (13 个文件)   JC_ERRORS=0   L0_RESULT=pass
# 消费者 E2E（test_package，真实 dlopen 两模块 + parse2 真链路）
RES=rc=0 E2E_ASSERTIONS_OK=74 E2E_ASSERTIONS_FAILED=0 FAILS=0
# 产物
lib/rsyslog/pmciscoios.so    76096 B  ELF64 AArch64 DYN  DT_NEEDED=[libc.so]
lib/rsyslog/pmcisconames.so  80192 B  ELF64 AArch64 DYN  DT_NEEDED=[libc.so]
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `lib/rsyslog/pmciscoios.so` | 76096 B | Cisco IOS parser 模块（`modInit` 入口） |
| `lib/rsyslog/pmcisconames.so` | 80192 B | Cisco 设备名反混淆 parser 模块（`modInit` 入口） |
| `packaging/rsyslog-cisco-8.2604.0-release.tar.gz` | 194608 B | 包目录快照（含 `lib/` + `licenses/`），本地产物不入 PR |

## 注意事项

1. 两个模块都是 parser 插件，必须由 `rsyslogd` 运行时 `loadmodule` 加载；本包不提供库供链接，
   `cpp_info.libs = []`，仅通过 `cpp_info` 属性 `rsyslog_modules_dir` 与
   `runenv_info RSYSLOG_MODDIR` 暴露模块目录。
2. 无命令行可执行产物 → **不声明 `commands.json`**（R38 针对 CLI 工具）。
3. 上游 `tests/` 未提供这两个模块的用例（仅 2 个 Cisco ASA 分帧用例，属 `imtcp`/`imptcp`，
   且需 rsyslogd 运行时），故模块级验证由 `test_package` 的消费者 E2E 承担（R51 台账见
   `test_package/MANIFEST.yml` 与 `reports/test-report.md`）。
4. `reports/`、`packaging/` 为本地元数据/产物（`.gitignore` 忽略），不进 PR。
---
**编译结束**: 2026-09-27 20:09
**最终状态**: built
