# rsyslog-testing 8.2604.0 适配笔记

## 编译环境
- 构建系统: autotools（configure + automake 递归 make）
- 编译日期: 2026-09-27 ~ 2026-09-30
- 编译器: clang（OHOS SDK 26.0.0.18，aarch64-linux-ohos，musl libc）
- 平台: HarmonyOS PC（aarch64）
- 状态: built

## 编译步骤

### 1. 制包（CI 口径，与 conanfile.py 逐字一致）

```bash
conan create . --build=missing          # profile: ohos-aarch64
```

配方内部实际执行：

```bash
./configure --disable-testbench --disable-uuid --disable-libgcrypt \
            --disable-openssl --disable-gnutls --disable-mbedtls \
            --disable-libsystemd --disable-jemalloc --disable-valgrind \
            --disable-diagtools --disable-usertools --disable-mysql \
            --disable-pgsql --disable-libdbi --disable-snmp \
            --disable-elasticsearch --disable-clickhouse --disable-omhttp \
            --disable-wolfssl --disable-libzstd --disable-relp \
            --disable-ksi-ls12 --disable-rfc3195 --disable-fmhttp \
            --disable-impstats-push --disable-impstats --disable-mmdblookup \
            --disable-omfile-hardened
make -C plugins/omtesting -j1 LIBS=      # 仅构建目标模块
```

产物：`lib/rsyslog/omtesting.so`（72064 字节，ELF aarch64/ET_DYN）。
本包按「官方全量源码包 + 仅编译打包目标模块」口径构建，**不构建 rsyslogd**。

### 2. 上游用例实跑（R51 三步法，本地 testbench）

上游 23 个 omtesting 相关用例全部经 `tests/diag.sh` 驱动**运行中的 rsyslogd**，
本包产物不含 rsyslogd，故补测在**独立 testbench** 中完成：

```bash
# (a) 源码树构建 rsyslogd（musl 缺口由本地垫片补齐，见第 4 节）
./configure --enable-testbench ... && make -j1 tools/rsyslogd   # → rsyslogd（3336704 字节）
# (b) 补编 harness 辅助程序（configure --disable-testbench 下不产出）
make -C tests test_id diagtalker chkseq mangle_qi msleep tcpflood
# (c) 逐用例运行（每个用例独立 rsyslogd 会话）
cd tests && srcdir=. bash ./execonlywhenprevsuspended.sh
```

实跑记录见第 6 节（25 项逐项结果与耗时，原始台账
`rst-cases.tsv`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `cannot guess build type`（E007） | 源码包自带 config.guess/config.sub（2022 年版）不识别 `uname -s = HarmonyOS` | 0001/0002 补丁补齐 HarmonyOS 识别，输出 `aarch64-unknown-linux-ohos` |
| 2 | configure 临时目录创建后构建进程不可写（E011） | HMDFS 下 `umask 077 && mktemp -d` 生成的目录按组权限语义不可写 | 0003 补丁把该块的 umask 放宽为 000（同 libestr / libfastjson / rsyslog 8.2404.0 口径） |
| 3 | 模块产出 `DT_NEEDED libz.so` 会让 loadmodule 失败 | configure 对 zlib 是硬性检查并把 `-lz` 注入全局 LIBS；而 `omtesting.c` 不引用任何 zlib 符号（`llvm-nm -u` 实测无 inflate/deflate/crc32/adler），目标机 `/usr/lib` 只有 `libz.so.1` 无 `libz.so` | 仅对模块目标传 `LIBS=`，清空注入的 `-lz` |
| 4 | 依赖头/库路径解析到 `-I//include -L//lib` | libestr/libfastjson 的 `.pc` 记录 `prefix="/"`（DESTDIR 风格），且 `cpp_info.libs` 名与真实链接名不同（estr / fastjson） | 沿用 rsyslog 8.2404.0 先例，以 `LIBESTR_*` / `LIBFASTJSON_*` / `ZLIB_*` 覆盖变量直指 conan 包内真实路径 |
| 5 | configure 因 impstats-push 中断 | 该特性默认自动启用且需 protoc-c，CI 无该工具链 | `--disable-impstats-push`（并显式关闭全部可选特性，避免探测结果随构建机漂移） |
| 6 | 上游用例中 rsyslogd 关机永不返回（本地 testbench） | **OHOS musl 无 `pthread_cancel`**（sysroot `libc.so` 导出 0 个取消符号），rsyslog 输入线程靠取消唤醒终止 → imdiag 输入线程永不退出，rsyslogd 日志实测 `trying to cooperatively stop input imdiag, timeout 60000 ms` | 仅**本地 testbench** 侧处理：调用方给关机加宽限（`RSTB_SHUTDOWN_GRACE`，默认 15s 后 SIGKILL 兜底），使 `diag.sh:wait_shutdown` 可收尾。**制品与补丁不含该改动**（见第 5 节） |
| 7 | 用例报 `./chkseq: No such file or directory` / `./mangle_qi: No such file or directory` | `--disable-testbench` 下 harness 辅助程序不构建 | 补编 `chkseq` / `mangle_qi` / `test_id` / `diagtalker`（仅本地 testbench） |
| 8 | 用例报 `bad interpreter: No such file or directory` | 设备无 `/bin/bash` | 本地 testbench 把用例/harness 的 shebang 指向设备可用 bash（`/data/service/hnp/bin/bash`） |
| 9 | 日志出现 `cat: Unknown option 'n'` | 设备 `cat` 不支持 `-n`（仅影响 `diag.sh` 失败时的诊断转储，不影响用例判定） | 未处理（不影响结果） |

## 源码修改

`patches/`（由 `apply_conandata_patches` 按序应用，均为 portability 类）：

| 补丁 | 内容 |
|------|------|
| `0001-config.guess.patch` | config.guess 识别 HarmonyOS → `aarch64-unknown-linux-ohos` |
| `0002-config.sub.patch` | config.sub 接受 `linux-ohos` 内核-OS 组合 |
| `0003-configure.patch` | configure 临时目录块 umask 077 → 000（HMDFS 可写性，E011） |

**制品源码零改动**：上游 C 源码未作任何修改（无 `__OHOS__` 条件编译、无 stub）。
第 4 节所述 musl 缺口（utmp/utmpx、`_res`、`pthread_cancel`）只出现在**本地 testbench**
（仅构建 `tools/rsyslogd` 供用例运行时使用），以 `-include` 垫片注入，**不进入本包制品，
也不进入 patches/**。

## 依赖版本

| 依赖 | 版本 | 制品仓 |
|------|------|--------|
| libestr | 0.1.11 | ✅ 已发布 |
| libfastjson | 1.2609.0 | ✅ 已发布 |
| zlib | 1.3.1.1 | ✅ 已发布（仅 configure 期依赖，不进模块 DT_NEEDED） |

## 验证结果

### 1) 制品校验（本地实测）

```bash
OMTESTING_MODULE=<pkg>/lib/rsyslog/omtesting.so \
OMTESTING_PACKAGE_FOLDER=<pkg> python3 test_package/check_omtesting.py
# → PASS=19  SKIP=0  FAIL=0  ；ALL CHECKS PASSED (rc=0)
```
覆盖：ELF aarch64/ET_DYN、`.dynstr` 导出、无 glibc 版本化符号、无
libz/libestr/libfastjson 动态依赖串、`DT_NEEDED` 仅 libc.so 且无 RPATH/RUNPATH、
licenses/COPYING、模块目录内容、readelf 动态段复核。

### 2) 消费者端到端用例（鸿蒙特有，本地实测）

```bash
clang -std=gnu11 -Wl,--export-dynamic -o omtesting_e2e \
      test_omtesting_e2e.c rsyslog_core_stub.c && ./omtesting_e2e <pkg>/lib/rsyslog/omtesting.so
# → E2E_ASSERTIONS_OK=62  E2E_ASSERTIONS_FAILED=0 (rc=0)
```
以真实消费者（rsyslogd）身份 `dlopen(RTLD_NOW)` → `modInit()` → 13 项入口表 →
`createInstance()`/`createWrkrInstance()`/`tryResume()`/`doAction()` →
`freeInstance`/`modExit` → `dlclose`，含负例（未知入口点不得解析）。

### 3) 上游 omtesting 相关用例实跑（R51）

- **清点**：`grep -rl omtesting tests --include='*.sh'` → 23 个上游用例；
  另计入 2 个通过 driver 变量引用同一驱动的父用例（`queue-persist.sh`、
  `daqueue-persist.sh`），台账共 25 项。
- **实跑环境**：HarmonyOS PC（aarch64）+ OHOS SDK clang，自建 rsyslogd testbench（第 2 节）。
- **结果**：**18 项实跑通过 / 7 项排除**（N=18 ≥ 1）。

| # | 用例 | 结果 | 耗时 |
|---|------|------|------|
| 1 | execonlywhenprevsuspended.sh | PASS | 19s |
| 2 | execonlywhenprevsuspended_multiwrkr.sh | PASS | 19s |
| 3 | execonlywhenprevsuspended-queue.sh | PASS | 19s |
| 4 | execonlywhenprevsuspended-nonsusp.sh | PASS | 18s |
| 5 | execonlywhenprevsuspended-nonsusp-queue.sh | PASS | 18s |
| 6 | execonlywhenprevsuspended2.sh | PASS | 19s |
| 7 | execonlywhenprevsuspended3.sh | PASS | 19s |
| 8 | execonlywhenprevsuspended4.sh | PASS | 18s |
| 9 | rscript_previous_action_suspended.sh | PASS | 18s |
| 10 | nested-call-shutdown.sh | PASS | 18s |
| 11 | da-queue-persist.sh | PASS | 20s |
| 12 | daqueue-dirty-shutdown-recovery.sh | PASS | 25s |
| 13 | daqueue-persist-drvr.sh | PASS | 35s |
| 14 | daqueue-invld-qi.sh | PASS | 35s |
| 15 | queue-persist.sh | PASS | 37s |
| 16 | diskqueue-truncated-segment-startup.sh | PASS | 48s |
| 17 | diskqueue-oncorruption-missing-segment.sh | PASS | 107s |
| 18 | diskqueue-full.sh | PASS | 124s |
| — | queue-encryption-da.sh | 排除 | — |
| — | queue-encryption-disk.sh | 排除 | — |
| — | queue-encryption-disk_keyfile.sh | 排除 | — |
| — | queue-encryption-disk_keyfile-vg.sh | 排除 | — |
| — | queue-encryption-disk_keyprog.sh | 排除 | — |
| — | daqueue-persist.sh | 排除 | — |
| — | queue-persist-drvr.sh | 排除 | — |

**排除项的技术原因**：

1. `queue-encryption-*.sh`（5 项）：用例要求队列加密 crypto provider
   （`lmcry_gcry.so` / `lmcry_ossl.so`）。本配方的 configure 明确
   `--disable-libgcrypt --disable-openssl --disable-gnutls --disable-mbedtls
   --disable-wolfssl`，且 OHOS sysroot 内无 libgcrypt，故该 provider 在本包
   构建范围内不存在 → 用例不适用于本包（非环境故障、非缺陷）。
2. `daqueue-persist.sh`：**上游自行禁用**——脚本打印
   `TEST is currently DISABLE because it is unstable` 并以 exit 77 退出
   （rsyslog 源码树自带声明），非适配问题。
3. `queue-persist-drvr.sh`：**非独立用例**，是 `queue-persist.sh` 通过
   `queue-persist-drvr` 变量调用的 driver 片段（自身不 `source diag.sh`，
   独立运行报 `generate_conf: command not found`）；其功能已由第 15 项
   `queue-persist.sh` 实跑覆盖。

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/rsyslog/omtesting.so` | 唯一制品产物（72064 字节） |
| `licenses/COPYING` | GPL-3.0-or-later |

## 注意事项

1. **本包产物只有模块**，不含 rsyslogd；上游用例需 rsyslogd 运行时方能执行，
   故 CI 不跑上游用例（`upstream_test_in_build: false`）。上游用例的实跑证据
   来自本机自建 testbench（第 2 节），台账与逐项结论见第 6 节。
2. **关机宽限属本地 harness 改动**：第 6 节问题 6 的 `RSTB_SHUTDOWN_GRACE` 只存在于
   本机 testbench 的 `diag.sh`，未进入 `patches/` 与制品；制品 `omtesting.so` 的
   功能路径（`doAction` / `tryResume` / 序列化）不受影响——端到端用例（第 5.2 节）
   直接驱动模块 API 即验证了这一点。
3. 模块以 `loadmodule` 方式被 rsyslogd 加载（`RSYSLOG_MODDIR` 指向
   `<pkg>/lib/rsyslog`），不作为链接库供消费者使用（`cpp_info.libs = []`）。

---

**编译结束**: 2026-09-30
**最终状态**: built
