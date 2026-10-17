# DRAFT-sexpp-0.9.1-gtest-captured-stream-tmp-hardcode：GTest CapturedStream 硬编码 /tmp，OHOS 只读 /tmp 下 CaptureStdout 用例 SIGABRT

> Contributor: pc2-30 | Status: Draft | Updated: 2026-09-16
> Source: sexpp 0.9.1 HarmonyOS PC 适配（GTest 1.14 CaptureStdout/CaptureStderr 用例在 OHOS 只读 /tmp 下 SIGABRT）

## 现象

OHOS 宿主 `/tmp` 是只读 erofs 挂载（`/dev/block/dm-0 on /tmp type erofs (ro)`）。
使用 GTest `testing::internal::CaptureStdout()/CaptureStderr()` 的上游用例
（如 sexpp 的 `ExceptionTests.SexpWarning`、`G23ExceptionTests.G23Warning`）
运行即 SIGABRT：

```
[WARNING] gtest-port.cc:1102: Failed to create tmp file /tmp/gtest_captured_stream.XXXXXX
[ FATAL ] gtest-port.cc:1126: Failed to open tmp file /tmp/gtest_captured_stream.XXXXXX
Signal 6 (core dumped)   # exit 134
```

按通用"只读 /tmp"经验（E002/E265/E363）`export TMPDIR=<可写目录>` **无效**——
GTest 的 `CapturedStream` 不读 TMPDIR/TMP/TEMP 任何环境变量，用例依然 SIGABRT。

## 与现有知识的关系

- E002/E363/E265 是通用 /tmp 只读 + **TMPDIR** 方案，适用于读 TMPDIR 的
  程序（多数 POSIX 工具与测试脚本）。
- DRAFT-ohos-check-framework-temp-env-not-tmpdir 是 check 框架特例：其
  `open_tmp_file()` 读 **TEMP** 而非 TMPDIR，注入 TEMP 可救。
- GTest 是第三类：`CapturedStream` 在非 Android/iOS 分支（gtest-port.cc
  `#else name_template = "/tmp/";`）**硬编码 `/tmp/`，不读任何环境变量**。
  现有索引无 GTest 捕获流特例条目。

## 方案

1. 先确认目标 GTest 版本捕获流路径分支：Android 分支用 `/data/local/tmp/`，
   iOS 分支用 `confstr(_CS_DARWIN_USER_TEMP_DIR)`（回退 TMPDIR），
   **其余（Linux/OHOS）分支硬编码 `/tmp/`**——无环境变量可覆盖。
2. 环境层无解（TMPDIR/TMP/TEMP 均无效），可行路径：
   - 若测试仅少数用例使用捕获流：`--gtest_filter` 排除后运行其余用例，
     捕获流用例如实记录为平台阻塞（计入分母不计通过），提供首错/命令/恢复条件；
   - 需要全量运行时：需可写 /tmp（root remount 或 CI worker 具备）或对 GTest
     打支持 TMPDIR 的补丁；
   - 注意 Android 分支特例：若 CI/设备以 `GTEST_OS_LINUX_ANDROID` 编译，
     捕获流走 `/data/local/tmp/`，不在此问题范围。
3. 台账如实体现：源码声明总数保留，阻塞用例逐项列首错、退出码、日志路径
   与恢复条件，不得把阻塞写成通过或未发现。

## 验证证据

- sexpp 0.9.1：82 个 TEST 中 80 个通过；2 个捕获流用例（SexpWarning、
  G23Warning）在专用临时目录 + `TMPDIR/TMP/TEMP` 三变量注入后仍 SIGABRT
  （gtest-port.cc:1090 硬编码 /tmp，mkstemp 失败 → FATAL）。
- `/tmp` 挂载证据：`mount` 输出 `/dev/block/dm-0 on /tmp type erofs (ro)`；
  `touch /tmp/x` → Read-only file system。
- 适用软件：所有用 GTest（>= 1.8 同类实现）做上游测试且用例含
  CaptureStdout/CaptureStderr、运行环境 /tmp 只读的库。
