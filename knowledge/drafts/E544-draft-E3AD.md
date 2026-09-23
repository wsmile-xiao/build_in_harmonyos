# E544 — OHOS /tmp、/var/tmp 只读导致上游硬编码临时路径测试失败

## 错误特征

```text
kj/filesystem-disk-test.c++:221: failed: mkstemp(filename.begin()): No such file or directory
kj/filesystem-disk-test.c++:232: failed: mkdtemp: No such file or directory; filename = /var/tmp/kj-filesystem-test.XXXXXX
kj/async-io-unix.c++:945: failed: ::bind(sockfd, &addr.generic, addrlen): Read-only file system; toString() = unix:/tmp/kj-async-io-test.NNNNN
capnp/serialize-test.c++:408: failed: expected (tmpfile.get()) >= (0) [-1 >= 0]
```

capnproto 1.3.0 上游测试在 OHOS 上运行时有 16 项失败，首错均为 mkstemp/mkdtemp/unix socket bind 指向 `/tmp`、`/var/tmp`。

## 触发条件

- 构建系统: cmake（BUILD_TESTING=ON 独立构建后运行测试二进制）
- 阶段: testing（测试运行）
- 前提: OHOS 平台 `/tmp`、`/var/tmp` 为只读挂载

## 根因分析

OHOS 的 `/tmp`、`/var/tmp` 是只读文件系统。上游测试源码**硬编码** `/tmp/...`、`/var/tmp/...` 路径（如 `mkstemp("/tmp/capnproto-serialize-test-XXXXXX")`、`mkdtemp("/var/tmp/kj-filesystem-test.XXXXXX")`、AF_UNIX socket `unix:/tmp/...`）。`TMPDIR` 环境变量只对使用 `$TMPDIR` 的用例生效，对硬编码路径的用例**无效**，因此该 16 项在 OHOS 必然失败；失败与库缺陷无关。

## 解决方案

### 推荐方案

- 配方范围（conanfile/patches）内**不改上游测试源码**（最小补丁原则，且测试非 CI 门禁输入）
- 受限用例按平台限制如实计入测试台账的 failed/未运行，并写明恢复条件（挂载可写 tmpfs 或真实设备可写 /tmp）
- 可规避用例以 `TMPDIR=~/tmp` 运行（kj/capnp 其余 993 项据此通过）
- 双口径统计：全量通过率以源码声明总数为分母（993/1069=92.9%），另列可执行集合通过率（993/1009=98.4%），未实例化项（win32 守卫、WITH_OPENSSL/ZLIB 门控）逐类说明

### 禁止做法

- ❌ 为绕过 /tmp 只读而修改/伪造测试源码或测试结果（门禁 FAIL 禁标 success）
- ❌ 把平台限制误报为当前库缺陷或依赖阻塞

## 验证

```bash
TMPDIR=~/tmp ./capnp-tests      # 224/225（1 项 /tmp 硬编码失败，平台限制）
TMPDIR=~/tmp ./kj-heavy-tests   # 437/452（15 项 /tmp、/var/tmp 硬编码失败，平台限制）
# 对照 reports/test-report.md 双口径台账逐项核对
```

## 关联条目

- 相关: E002（/tmp 只读 + TMPDIR，configure 阶段）、E024（AF_UNIX bind 权限）、E136（TMPDIR/mktemp 配置阶段）
