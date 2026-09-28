# gtest CaptureStderr/CaptureStdout 硬编码 /tmp, TMPDIR 无效 (OHOS)

## 问题

在 OHOS（HarmonyOS PC, arm64）上运行依赖 gtest `testing::internal::CaptureStderr()` /
`CaptureStdout()` 的上游测试时, ctest 报 **Subprocess aborted**, 首错为:

```
[WARNING] .../gtest-port.cc:1144:: Failed to create tmp file /tmp/gtest_captured_stream.XXXXXX
[FATAL]   .../gtest-port.cc:1168:: Failed to open tmp file /tmp/gtest_captured_stream.XXXXXX
```

lunarlog 1.29.2 上游 1157 个用例中 4 项命中: `RollingFileTest.EnsureOpenFailure`、
`RollingFileTest.RenameFailureDuringRotation`、`FileTransportTest.WriteFailureTriggersErrorPath`、
`FileTransportTest.ErrorReportedFlagSuppressesDuplicateStderr`。

## 根因

1. OHOS 系统 `/tmp` 为 erofs 只读挂载 (`touch /tmp/x` → Read-only file system)。
2. gtest `CaptureStream()` 的临时文件路径按平台分支选择 (gtest-port.cc):
   - `GTEST_OS_LINUX_ANDROID`: 调用 `TempDir()` — **读取 TMPDIR 环境变量**;
   - `GTEST_OS_IOS`: 走 `confstr(_CS_DARWIN_USER_TEMP_DIR)`（回退 getenv("TMPDIR")）;
   - **其余所有平台（含 OHOS / 通用 Linux）: 硬编码 `name_template = "/tmp/"`**, 完全不读 TMPDIR/TMP/TEMP。
3. 只读 `/tmp` 上 `mkstemp` 失败 → `GTEST_CHECK_` 触发 → 进程 abort → ctest 报 Subprocess aborted。

关键点: **gtest 捕获流不是临时目录问题中"设置 TMPDIR 即可"的场景**——该分支读环境变量只在
Android/iOS 上成立, 通用 POSIX 分支硬编码 /tmp。

## 方案

1. 先按上游测试临时目录恢复规则执行恢复尝试（必须做）:
   - 创建用户可写专用临时目录, `chmod 700` + `stat` 验证;
   - 设置 `TMPDIR`/`TMP`/`TEMP` 后以同一入口重跑。
2. 同一首错复现（gtest 捕获流仍写 /tmp）时, 如实归类为**平台/框架基础设施阻塞**:
   - 计入上游测试总分母, 不计为通过, 也不计为失败;
   - 恢复条件写清: 需可写 /tmp（重新挂载/bind tmpfs）或 gtest 增加 TMPDIR 支持;
   - 不得修改上游测试跳过、不得伪造通过。
3. 候选临时目录需满足真实 `0700` 语义: OHOS HMDFS 不保留 POSIX 权限位
   （`chmod 700` 后 stat 显示 `drwxrws--x` 2771）, 只可写不保留权限位的目录不合格,
   需继续尝试设备上实际存在的 tmpfs/ext4 挂载点; 但即便目录合格, gtest 捕获流仍写 /tmp,
   因此最终归类仍为平台阻塞。

## 验证

- `touch /tmp/.probe_write` → `Read-only file system`
- `TMPDIR=<writable dir> TMP=<dir> TEMP=<dir> ctest -R RollingFileTest.EnsureOpenFailure` →
  仍报 `/tmp/gtest_captured_stream.XXXXXX` 同一首错
- gtest-port.cc:1132 源码确认 `name_template = "/tmp/";`（非 Android 分支）
- 日志: lunarlog reports/upstream_ctest.log、baseline_isolation_rerun.log（SHA-256 见回报）

## 适用边界

- 适用: OHOS 及任何 /tmp 只读、非 Android 的 POSIX 平台上的 gtest 捕获流类测试
- 反例: Android 平台读 TMPDIR 不适用本结论; 无 CaptureStderr/CaptureStdout 的普通 gtest
  用例不受影响（lunarlog 其余 1153 项正常执行）

## 关系

- caused_by: E002（/tmp 只读）
- similar_to: E002, E110, E292
- 来源: lunarlog 1.29.2 OHOS 适配 (executor pc7-21), 2026-09-23
