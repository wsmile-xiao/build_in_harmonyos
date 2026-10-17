# DRAFT-postgresql-sysv-shmget-eacces-spin：shmget 返回 EACCES 引发 for(;;) 无限自旋

## 现象

`initdb` / `postgres --check -F` 进程以 ~85% CPU 自旋不退出，无任何错误输出，
`wchan=0, State=R（running）`。独立探针：`shmget(IPC_PRIVATE, 4096, IPC_CREAT|IPC_EXCL|0600)`
返回 `Permission denied (errno=13)`（**不是** signal 31 / SIGSYS）。

```text
$ ./shmget_test
shmget failed: Permission denied (errno=13)
```

## 根因

OHOS 沙箱对 SysV 共享内存 syscall 的拦截有两种表现：AFL++ 等记录的是 SIGSYS
（signal 31，进程被终止，见 DRAFT-ohos-sysv-shmget-sigsys）；本环境实测为
**EACCES（Permission denied）**。PG16 `PGSharedMemoryCreate`（sysv_shmem.c）的
`for(;;)` 探测循环把所有 EACCES 归类为 `SHMSTATE_FOREIGN` → `NextShmemSegID++`
→ 无限重试探测下一个 key，永不退出（自旋），且无日志输出。

## 修复（PG 语义宏守卫，配合内建 mmap 主共享内存）

PG 的 `shared_memory_type=mmap` 路径本就使用 anonymous mmap（CreateAnonymousSegment）
承载数据，SysV 段只用于互锁（header），因此可直接跳过。HAVE_BROKEN_SHMGET 守卫：

1. `InternalIpcMemoryCreate()`：直接返回 `static PGShmemHeader fake_header`（memset 0），
   不再调用 shmget
2. `PGSharedMemoryIsInUse()`：返回 `false`（不探测）
3. `PGSharedMemoryAttach()`：`*addr=NULL; return SHMSTATE_ENOENT;`
4. `IpcMemoryDetach()` / `IpcMemoryDelete()`：空实现

宏由 conanfile.py generate() 仅 OHOS 构建注入（R8：补丁内无平台宏）。

## 适用边界

- 数据库/服务端应用调用 SysV 共享内存，且**存在内建 mmap/其他共享内存通道**时，用守卫跳过互锁即可
- 无内建替代的工具（如 afl 家族）仍需 POSIX shm_open+mmap 替换（DRAFT-ohos-sysv-shmget-sigsys）
- 与 SIGSYS 表现区分：SIGSYS=进程被杀（快速失败）；EACCES=被当作 FOREIGN 无限自旋（隐蔽挂起）

## 验证证据

- initdb exit 0、pg_ctl start、真实连接 SQL 通过（consumer exit 0）
- make check 216/217（opr_sanity 为 ELF 签名平台限制）

## 查重关系

- similar_to: DRAFT-ohos-sysv-shmget-sigsys（同 syscall 家族，不同失败表现与解法）、E051
- caused_by: 无
- prerequisite_of: 无
- conflicts_with: 无
- 反例：有内建 mmap 通道但需要跨进程互锁语义的应用，跳过互锁后需验证数据一致性由其他锁保证