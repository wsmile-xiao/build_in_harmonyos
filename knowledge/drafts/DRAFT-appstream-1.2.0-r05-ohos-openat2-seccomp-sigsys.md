# DRAFT-appstream-1.2.0-r05-ohos-openat2-seccomp-sigsys — seccomp 落杀型平台：能力探针包 SIGSYS handler + sigsetjmp 回退

> **Contributor**: pc2-19 | **Status**: DRAFT | **Updated**: 2026-09-25
> **Severity**: medium (2) | **Category**: syscall / seccomp / SIGSYS / openat2
> **Audience**: 在 seccomp 落杀（SIGSYS）型平台上做 syscall 能力探测的代码

## 触发（trigger）

- appstream 1.2.0（archives/a/appstream/1.2.0，R05）：as-test_compose DirectoryUnit 段
  rc=159（128+31=SIGSYS），进程直接被杀，无任何错误返回。

## 症状（symptom）

```
rc=159  # SIGSYS：进程被信号 31 杀死
```

## 机制（root cause）

OHOS seccomp 对 `openat2()`（SYS_openat2）直接落杀，而非返回 `ENOSYS/EPERM`。
上游 `asc_openat2_usable()` 探针假定"调用失败会返回错误码"，于是探针自身
第一次执行即被信号杀死，无法优雅回退到用户态路径解析。

## 修复（fix）

0016-asc-directory-unit.patch：探针执行前安装 SIGSYS handler 并用
`sigsetjmp` 记录现场；handler 内 `siglongjmp` 回到探针；被打断视为
"openat2 不可用"，走 `asc_resolve_path_in_root()` 用户态路径解析，
并恢复原 SIGSYS handler。

## 验证（verification）

- as-test_compose DirectoryUnit / DirectoryUnitEscape 通过（rc=0），
  日志可见 `openat2() is blocked by a sandbox (SIGSYS), will resolve paths in userspace`.

## 适用边界 / 反例

- 适用：seccomp 落杀型平台上的任何 syscall 能力探测（openat2、clone3 等）；
- 反例：syscall 正常返回 ENOSYS 的平台无需 handler（返回码路径已可处理）。

## 关系

- 查重：E051（未实现 syscall→SIGSYS）覆盖 setreuid 等**不存在**的 syscall，方案是
  EXCLUDE_LIST 排除；本候选是**存在但被 seccomp 拦截**，方案是探针 sigsetjmp 防护 + 回退。
- similar_to: E051；caused_by: []; prerequisite_of: []; conflicts_with: []

## 证据

- 补丁：patches/0016-asc-directory-unit-openat2-sigsys.patch
- 台账：archives/a/appstream/1.2.0/reports/knowledge-candidate-ledger.md 候选 16
