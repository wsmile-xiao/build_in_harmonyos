# qprint 1.1.dfsg.2 知识证据报告

- 真机：10.195.180.238，隔离 job `device-b/qprint-kb-20260920`；2026-09-20

## EVID-01 失败基线（两轮，target-executed）

```text
./config.status:602: permission denied: ./confFAGLbI/subs1.awk
config.status: error: could not setup config files machinery
```

## EVID-02 umask 对照实验（target-executed）

```text
$ umask 077; D=$(mktemp -d ./confXXXXXX); ls -ld $D
drwx--S--- ... → echo hi > $D/f → Permission denied
$ （同目录 umask 022 建目录）→ drwxrws--x → 写入成功
```

## EVID-03 修复后全绿（target-executed）

conan create 退出码 0；消费者输出：`roundtrip: OK` / `known-value: OK` /
`test_qprint: OK (encode/decode roundtrip + known-value)`（-e/-b 编码后 -d/-b
解码逐字节一致 + `=` → `=3D`）。产物：bin/qprint + share/man/man1/qprint.1。

## 测试统计

上游 0（清点：无 tests/、无 make check 目标）；消费者 2/2。

## 影子 CI

- 原失败：#59789 在 `conan-build-test` 阶段应用 `0002-Makefile-in-installdirs.patch` 失败。
- 修复后真机回归（2026-09-24）：补丁、构建、安装和 consumer 2/2 全部通过。
- 远端 CI #60062：`CI 校验通过`（功能修复提交 `c9308177`）。
- 远端 CI #60070：`CI 校验通过`（知识证据提交 `7c625c93`）。
