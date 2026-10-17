# DRAFT-postgresql-fallocate-eacces-filezero：FileFallocate 应将 EACCES/EPERM 与 EINVAL/EOPNOTSUPP 同等回退

## 现象

`make check` 首轮 **48/217 测试失败**，共同错误：

```text
ERROR: could not extend file "base/16384/16412" with FileFallocate(): Permission denied
HINT:  Check free disk space.
```

## 根因

PG16 `src/backend/storage/file/fd.c` 的 `FileFallocate()` 只对
`EINVAL`/`EOPNOTSUPP` 回退到 `FileZero()`（逐块零填充），把其他错误当"真实失败"
返回。OHOS 的 hmdfs 文件系统上 `posix_fallocate()` 返回 **EACCES（Permission
denied）**（与 E523 记录的 Go 链接器同根因，但触发阶段不同：本处是运行时数据库
relation extension，E523 是 linking 阶段），于是所有需要预分配空间的表写入失败，
波及 48 个测试（test_setup 的数据 COPY 失败引发级联失败）。

## 修复

HAVE_BROKEN_FALLOCATE 语义宏（conanfile 仅 OHOS 注入，R8 语义宏）把
`EACCES`/`EPERM` 与 `EINVAL`/`EOPNOTSUPP` 一并纳入回退集合 → `FileZero()`：

```c
#ifdef HAVE_BROKEN_FALLOCATE
	if (returnCode != EINVAL && returnCode != EOPNOTSUPP &&
		returnCode != EACCES && returnCode != EPERM)
		return -1;
#else
	if (returnCode != EINVAL && returnCode != EOPNOTSUPP)
		return -1;
#endif
```

## 适用边界

- 调用 fallocate/posix_fallocate 且写入路径可回退到零填充的 C/C++ 应用（数据库、文件工具）
- hmdfs/tmpfs 等 fallocate 被拒（EACCES/EPERM）的文件系统
- 反例：依赖 fallocate 原子分配语义（如避免 OOM 预分配）且无零填充回退面的场景，不能套用

## 验证证据

- 修复前 make check 48/217 失败 → 修复后 **216/217**（唯一失败 opr_sanity = ELF 签名平台限制）
- 消费者用例真实连接 SQL 通过

## 查重关系

- similar_to: E523（fallocate EACCES on HMDFS，Go 链接器 toolexec wrapper——linking 阶段解法不同）、E115（fallocate 常量缺失，编译期）
- caused_by: 无
- prerequisite_of: 无
- conflicts_with: 无
- 差异轴：E523 是 linking 阶段绕开（toolexec）；本条目是运行时调用点把 EACCES/EPERM 加入回退集合（数据库层）