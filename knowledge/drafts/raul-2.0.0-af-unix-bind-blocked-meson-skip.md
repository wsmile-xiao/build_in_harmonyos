# raul 2.0.0 — OHOS 拒绝 AF_UNIX bind 的平台能力探测 + meson skip（draft）

**Category**: ohos | portability | test | network · **Severity**: 2 · **Tool**: meson

## 症状

OHOS 真机/CI 上运行上游 socket 测试失败：

```
Assertion failed: unix_server_sock.bind(unix_uri) (../test/socket_test.cpp: main: 27)
Signal 6 (core dumped)
```

## 根因（比"E002 /tmp 只读"更准确）

OHOS 安全策略整体拒绝 AF_UNIX bind，不只是 /tmp 权限问题：

| 目标路径 | 结果 |
|---|---|
| `/tmp/raul_test_sock` | bind errno=EROFS=30（/tmp 只读，E002） |
| `$TMPDIR/…`（可写） | bind errno=EPERM=1（Operation not permitted） |
| `./…`（cwd 可写） | bind errno=EPERM=1 |
| `/data/local/tmp/…` | bind errno=EACCES=13 |
| TCP 回环 `127.0.0.1:0` | ✅ bind OK |

python AF_UNIX 探针可 10 秒复现。**改路径无法修复**（本包初版补丁改 TMPDIR 后
仍失败），属平台能力缺失而非库缺陷。

## 对策（只改失败分支，断言零改动）

```cpp
  if (!unix_server_sock.bind(unix_uri)) {
    const int bind_errno = errno;
    if (bind_errno == EPERM || bind_errno == EROFS || bind_errno == EACCES) {
      // HarmonyOS denies AF_UNIX bind (EPERM) and mounts /tmp read-only;
      // report a meson-level skip (exit code 77) instead of failing.
      fprintf(stderr, "AF_UNIX bind not permitted (errno=%d); skipping\n", bind_errno);
      return 77; // meson 将退出码 77 记为 SKIP
    }
    fprintf(stderr, "unexpected AF_UNIX bind failure (errno=%d)\n", bind_errno);
    return 1;    // 非平台原因仍 FAIL，不掩盖真实缺陷
  }
```

另补 `#include <cerrno>`；补丁经 `refresh-patch --auto` 生成，conandata 以
`patches` 列表声明（`patch_type: portability`，无平台宏）。

## 验证

raul 2.0.0（2026-09-20，HarmonyOS 6.1.0.117 aarch64，clang 15.0.4）：
补丁前 SIGABRT；补丁后 `meson test` `Ok: 10 / Fail: 0 / Skipped: 1`，
消费者测试 40/40。

## 适用边界

适用于测试中的 AF_UNIX 辅助用例；若 AF_UNIX 是功能路径本身，应如实申报
平台不支持或改用 TCP 回环等价验证。
