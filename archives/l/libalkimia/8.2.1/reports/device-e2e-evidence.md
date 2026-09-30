# libalkimia 8.2.1 真机端到端证据（DAYU200 / OpenHarmony 6.0.0.47）

消费者端到端用例 `test_package/test_libalkimia.cpp`（23 个校验点）在**真机**上执行，
验证安装产物（`LibAlkimia6Config.cmake` → `Alkimia::alkimia`）在 OpenHarmony
aarch64 运行时的完整可用性。

## 1. 设备与环境

| 项 | 值 |
|---|---|
| 设备 | DAYU200-RK3568 |
| 系统 | OpenHarmony 6.0.0.47（API20，aarch64，64bit） |
| 序列号 | `450100445634303332018f3e7d2dba00` |
| 远端目录 | `/data/local/tmp/ohpc_test/libalkimia_e2e/` |
| 执行命令 | `cd /data/local/tmp/ohpc_test/libalkimia_e2e && sh run.sh` |
| 时间戳 | 2026-09-29T20:13:57+08:00 |
| 退出码 | **0** |

## 2. payload 构造（真机可运行闭包）

真机 `/system/lib64` 之外的依赖（Qt6 / KF6 6.18 / gmp / zstd 等）不在设备镜像内，
因此把**测试二进制及其全部 `DT_NEEDED` 闭包**（34 个 aarch64 动态库 + 二进制，
75 MB）平铺到同一目录，并做两步归一化：

1. **闭包解析**：以配方运行期同款库搜索顺序（测试二进制链接的全部 conan 包 `lib/`
   目录，按序去重 + OHOS runroot）逐层解析 `DT_NEEDED`，并逐个校验
   `readelf -h` 为 `AArch64`（避免同名异架构/异变体库被误打包）。
   实测：解析 34 个库，**无缺失**、**无同名多源冲突**。
2. **NEEDED 归一化**：把已发布 KF6/Qt 包遗留的**路径型** `DT_NEEDED`
   （`../../bin/libKF6*.so`、`/storage/Users/currentUser/.cache/conan2/p/...` 等）
   用 `patchelf --replace-needed` 重写为裸 basename，并清除 RPATH；
   运行期由 `run.sh` 的 `LD_LIBRARY_PATH=<payload>:/system/lib64` 解析
   （OHOS musl 不按 `LD_LIBRARY_PATH` 解析路径型 NEEDED，故必须先归一化）。

`run.sh`：

```sh
#!/bin/sh
cd "$(dirname "$0")"
export LD_LIBRARY_PATH="$(pwd):/system/lib64"
export HOME=/data/local/tmp/ohpc_test/libalkimia_e2e/home
export TZ=UTC
mkdir -p "$HOME"
./test_libalkimia
rc=$?
echo "EXIT_CODE=$rc"
exit $rc
```

## 3. 真机原始输出（节选，完整 23 行 ok）

```
== payload files: 37 ==
== LD_LIBRARY_PATH=/data/local/tmp/ohpc_test/libalkimia_e2e:/system/lib64 ==
libalkimia consumer e2e (package libalkimia/8.2.1)
--- case1 金融金额计算回环 (AlkValue) ---
ok 01 1.1 parse 'x1.234,568 EUR' (comma decimal) -> 154321/125
ok 02 1.2 parse '10.25' -> 41/4
ok 03 1.3 ledger sum 10.25+5.75-3.50 -> 25/2
ok 04 1.4 multiply 25/2 * 4 -> 50/1
ok 05 1.5 divide 50/1 / 8 -> 25/4
ok 06 1.6 convertDenominator(100, RoundFloor) 2.345 -> 117/50
ok 07 1.7 convertDenominator(100, RoundCeil) 2.345 -> 47/20
ok 08 1.8 toString->reparse fraction round-trip equals
ok 09 1.9 decimal '12.50' equals ledger sum
ok 10 1.10 double ctor 1.5 -> 3/2
ok 11 1.11 precision<->denominator helpers (2<->100, 1000->3)
ok 12 1.12 comparison operators (>, <, !=, ==)
--- case2 报价源存储回环 (AlkOnlineQuoteSource) ---
ok 13 2.1 defaultCurrencyQuoteSource write() persists
ok 14 2.2 reloaded source isValid()
ok 15 2.3 reloaded fields match written source
ok 16 2.4 profile.quoteSources() contains 'e2e-currency'
ok 17 2.5 custom CSV source write/read url round-trip
ok 18 2.6 custom CSV source format/regex fields round-trip
ok 19 2.7 rename -> reloaded under new name
ok 20 2.8 remove -> store entries gone
--- case3 报价引擎消费者契约 (AlkOnlineQuote) ---
ok 21 3.1 AlkOnlineQuote constructed, setUseSingleQuoteSignal(true) readback
ok 22 3.2 single-quote signal toggle back to false
ok 23 3.3 launch() with unknown source returns false (no download)
RESULT: 23 checks, 0 failures
ALL_CONSUMER_TESTS_PASSED
EXIT_CODE=0
```

## 4. 设备证据文件

见同目录 `device-e2e-_device_evidence.json`（由设备执行脚本写入，
含 `job` / `device_serial` / `system` / `command` / `exit_code` / `timestamp`）：

```json
{
  "job": "libalkimia_e2e",
  "device_serial": "450100445634303332018f3e7d2dba00",
  "system": "OpenHarmony 6.0.0.47 (API20, aarch64, 64bit)",
  "command": "sh run.sh",
  "exit_code": 0,
  "timestamp": "2026-09-29T20:13:57+08:00"
}
```

## 5. 汇总

| 口径 | 结果 |
|---|---|
| 本地 `conan create` test_package（qemu/ohos-aarch64-run） | 23/23 通过，`RESULT: 23 checks, 0 failures` |
| DAYU200 真机 | 23/23 通过，退出码 0 |
| 上游 CTest（离线口径） | 9/9 通过（100%） |

## 附录：真实下载路径的真机崩溃原始输出（既有缺陷记录）

同一 payload 机制下、加入「内嵌 QTcpServer + `AlkOnlineQuote::launch` 真实 HTTP
下载」探针后，真机输出（与 qemu 仿真一致）：

```
ok 21 3.1 embedded quote HTTP service listening on 127.0.0.1
ok 22 3.2 consumer quote source configured and persisted
Alkimia: bool AlkOnlineQuote::Private::applyDateRange(QUrl &) "http://127.0.0.1:46419/quote.csv?a=ALKIMIA"
Signal 11
EXIT_CODE=139
```

技术分析见 `upstream-test-evidence.md` 第 3 节：该路径在 OHOS musl 运行时下
`SIGSEGV`（仿真与真机一致复现），属既有缺陷，与本轮适配改动无关；正式的消费者
端到端用例因此不触发真实下载。
