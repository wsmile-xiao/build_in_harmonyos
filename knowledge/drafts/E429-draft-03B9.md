# E429 草稿：OHOS 中 POSIX 共享内存与信号量同名冲突

## 现象与范围

Qt Base 6.11.1 的 `tst_qsharedmemory` 在 POSIX 模式下创建新对象却报告
`QSharedMemory::attach (shm_open): already exists`；附加不存在的共享内存反而成功。
同一轮信号量测试通过。环境为 HarmonyOS PC / HongMeng Kernel 1.12.0，
HiShell 应用进程，OHOS Clang 15.0.4。本结论限定到该实测运行时。

## 原因与独立复现

`QSharedMemoryPrivate::semaphoreNativeKey()` 假设 POSIX 信号量与共享内存
位于不同命名空间，返回同一 native key。设备上的两个 API 实际共享名称：
内部锁先创建了 32 字节的信号量对象，随后的共享内存创建碰撞；附加操作甚至会
打开这个信号量对象。这与头文件、链接符号或整体缺少 POSIX IPC 是不同的问题。

在本机任务专用目录编译以下程序，并在同一目标运行环境执行：

```c
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <semaphore.h>
#include <stdio.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
int main(void) {
    char name[80];
    snprintf(name, sizeof name, "/ipc-namespace-probe-%ld", (long)getpid());
    sem_t *sem = sem_open(name, O_CREAT | O_EXCL, 0600, 1);
    if (sem == SEM_FAILED) return 2;
    errno = 0;
    int fd = shm_open(name, O_CREAT | O_EXCL | O_RDWR, 0600);
    printf("same-name create: fd=%d errno=%d\n", fd, errno);
    if (fd >= 0) close(fd);
    fd = shm_open(name, O_RDONLY, 0);
    struct stat st = {0};
    if (fd >= 0) fstat(fd, &st);
    printf("same-name open: fd=%d size=%ld\n", fd, (long)st.st_size);
    if (fd >= 0) close(fd);
    sem_close(sem);
    sem_unlink(name);
    shm_unlink(name);
}
```

```sh
clang ipc-namespace-probe.c -o ipc-namespace-probe
./ipc-namespace-probe
```

实测：先创建信号量后，`shm_open(O_CREAT|O_EXCL)` 返回 `-1/EEXIST`，
只读打开成功且大小为 32。反向先创建共享内存，再排他创建同名信号量也返回
`EEXIST`。完整双向程序为外部交付目录中的 `ipc_namespace50.c`，原始执行记录
为 QtBase HDC 队列 `c044`。程序只清理自身 PID 派生的名称。

## 修复与验证状态

适配补丁 0023 先把完整原名计算为 64 个十六进制字符的 SHA256，再使用 Qt 既有的
`QSystemSemaphore::legacyNativeKey()` 为内部锁生成带信号量前缀的确定性名称。
用户可见的共享内存 native key 保持不变；锁、排他创建和错误传播继续执行。
不同进程从相同共享内存 key 得到相同内部锁名称。

原始 22 补丁运行中，共享内存测试记录 36 通过、30 失败、14 跳过。
修复后完整共享内存程序通过，随后重复执行也通过。原用例的固定遗留 key 曾在
重复执行时碰撞：Qt POSIX detach 保留名称，而用例未登记清理。补丁 0024 使用
上游已有 PID/序号命名和清理机制，保留 create/attach 的原始行为断言。

独立新消费者用 221 字节 native key 启动两个子进程，各在持锁状态下执行
200 次读、等待、写操作，父进程核验正常退出及最终精确值 400。final63 真机
44 个必测断言全部通过，其中包含该用例。旧库的相同长名称探针编译成功，运行
报告内部信号量名称过长；旧失败与新通过都已保存。子进程结束后仅清理本用例
拥有的随机名称。

当前配方只接受原生 OHOS armv8；若向其他平台复用此通用源码修改，需要保留
Darwin 沙箱的应用组名称约定并单独验证。此处的运行结论仅来自上述 OHOS 环境。

## 查重与价值边界

在官方提交 `090ac16c6` 的知识目录检索 `sem_open`、`shm_open`、同名空间及
共享内存相关词，现有 libc 能力表记录 API 存在，没有这个双向名称冲突及 Qt 内部
锁映射问题。此条目是待审知识草稿，编号和路径类别由主编确定。

保留原错误和检查同步语义，避免通过忽略 EEXIST 或移除内部锁制造通过结果。
