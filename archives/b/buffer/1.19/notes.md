# buffer 1.19 适配笔记

## 编译环境

- 构建系统: makefile（上游 raw Makefile，无 configure/CMake）
- 编译日期: 2026-09-14
- 编译器: clang 15.0.4（OHOS SDK 26.0.0.18，aarch64-linux-ohos）
- 状态: built
- 源码 SHA256: `a9d5c9a384bb7b608594aca3010aa090dfb18445198c0a95c63b8bd376d4cafb`

## 编译步骤

```bash
# 1) 取源码（Fedora dist-git 官方 lookaside 缓存；上游官网已下线）
curl -fsSL -o buffer-1.19.tar.gz \
  "https://src.fedoraproject.org/repo/pkgs/buffer/buffer-1.19.tar.gz/e1e953f2a977753c5053b8ecf6c4f3f0/buffer-1.19.tar.gz"
sha256sum buffer-1.19.tar.gz   # a9d5c9a384bb7b608594aca3010aa090dfb18445198c0a95c63b8bd376d4cafb

# 2) 解压后套用补丁并构建（conan create 实际执行路径）
make CC=clang CFLAGS="-Wall" -j1     # → ./buffer
```

上游 Makefile 只有 `all: buffer`（依赖内置 `.c→.o` 规则）和一个直接写 `/usr/local` 的
`install` 目标；打包由 `conanfile.py` 的 `package()` 完成（`bin/buffer`、手册页
`share/man/man1/buffer.1`、`licenses/COPYING`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 程序启动即 `Bad system call (core dumped)`（SIGSYS / signal 31 / exit 159），连参数解析都过不去 | OHOS 沙箱拦截 System V IPC：`shmget`/`semget`/`msgget` 被内核以 SIGSYS 终止（实测：单独调 `shmget` 的 10 行 C 程序同样被终止；`kernel.shmall`/`shmmax` 存在而 `kernel.sem`/`msgmax` 不存在；同型公开问题：OpenHarmony third_party_musl issue I5MQ9A「shmget 接口报错 signal 31」） | 补丁 0001：共享内存改为 `shm_open + ftruncate + mmap(MAP_SHARED)`，释放改为 `munmap + shm_unlink`（同 afl 1.35b 先例） |
| 2 | `sem.c` 无法编译：`variable has incomplete type 'union semun'` | musl 侧 `sys/sem.h` 只置 `_SEM_SEMUN_UNDEFINED 1`，从不定义 `union semun` | 补丁 0002 把整个 SysV 信号量实现换成 POSIX 进程间信号量，该类型问题随之消失 |
| 3 | `buffer.c` 编译错误：`conflicting types for 'shmat'` | 1990 年代的 K&R 前置声明 `extern char *shmat();` 与现代 `sys/shm.h` 的 `void *shmat(int, const void *, int)` 冲突 | 补丁 0001 删除该过时声明（`sys/shm.h` 已被包含），改用头文件里的原型 |
| 4 | `sem.c` 编译错误：`non-void function 'do_sem' should return a value` | `static do_sem(...)` 是隐式 int 返回的 K&R 写法 | 该函数在补丁 0002 中被 POSIX 实现取代，不再存在 |
| 5 | 运行期无 `sleep`/`MemFree` 相关异常 | — | 单进程峰值内存 ≈ `-m` 指定值（默认 1 MiB），构建 `-j1` |

## 源码修改

两个补丁（均在 `patches/`，`conandata.yml` 以列表形式声明）：

1. **`0001-buffer.c.patch`**（+53/-19）
   - 删除 `#ifndef __alpha / extern char *shmat(); / #endif`（与现代原型冲突的过时声明）
   - `#include <sys/shm.h>`、`<sys/sem.h>` → `#include <sys/mman.h>`；补 `#include <stdlib.h>`
   - 新增 `shm_fd`/`shm_name`，`buffer_allocate()` 用 `shm_open(O_CREAT|O_EXCL)` +
     `ftruncate(buffer_size)` 建段；`get_buffer()` 用 `mmap(MAP_SHARED)` 映射；
     `buffer_remove()` 用 `munmap` + `shm_unlink` 释放
2. **`0002-sem.c.patch`**（+70/-63）
   - 整段替换 SysV 实现：`new_sems()` 在 `MAP_SHARED|MAP_ANONYMOUS` 映射里放
     `sem_t` 数组（`sem_init(pshared=1)`，初值 1，与上游 `sem_set(sem,i,1)` 一致）；
     `sem_set()`/`lock()`/`unlock()`/`remove_sems()` 分别对应
     `sem_init` 重置 / `sem_wait` / `sem_post` / `sem_destroy+munmap`
   - 语义与原来一一对应，不含任何 `__OHOS__` 平台宏；Linux 上同样可编译运行

**未修改上游测试用例**（上游无测试套件，N = 0，见下）。

## 依赖版本

- 无第三方依赖（`requires()` 为空；不需要任何 `tool_requires`，raw make + OHOS SDK clang）

## 验证结果

```bash
# 设备实机（OHOS aarch64 / clang 15.0.4）
$ make CC=clang CFLAGS="-Wall" -j1 && echo BUILD-OK
BUILD-OK
$ head -c 31457280 /dev/urandom > big.bin && ./buffer < big.bin > out.bin && cmp big.bin out.bin && echo IDENTICAL
IDENTICAL                       # 30 MiB 随机数据往返，逐字节一致
$ for n in 1 2 3 7 10239 10240 10241 20479 20480 20481 100000 1048577; do ... done
12/12 OK                        # 分块边界尺寸扫描
$ ./buffer -B < in(200000B) > out && wc -c < out
204800                          # 末块补齐到 10240 的整数倍，前缀一致
$ ./buffer -s 65536 -b 8/-m 65536 ...; cmp
IDENTICAL                       # 参数化分块与共享内存上限
$ 3 实例并发往返 + 30 轮连续运行
0 失败                          # 无共享内存/信号量泄漏，无残留进程
```

`test_package`（鸿蒙侧消费者用例，5 条）全部通过，见 `reports/test-report.md`。
上游测试：上游无任何测试入口，N = 0，运行数 N′ = 0（不适用——上游 0 个可运行测试入口）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/buffer` | ~34 KB | 重分块过滤器（PIE + RELRO + BIND_NOW，NX stack） |
| `share/man/man1/buffer.1` | 5.1 KB | 上游手册页（`buffer.man` 按段号 1 安装） |
| `licenses/COPYING` | 18 KB | GPL 许可证原文 |

## 注意事项

- **SysV IPC 不可用是本包的核心适配点**：任何后续版本（上游最后更新为 1995 年，
  无 1.20）或同族工具（用 `shmget`/`semget`/`msgget` 的程序）都要先做同样的替换，
  否则在 OHOS 上会以 SIGSYS 崩溃，且错误信息（`Bad system call`）完全不指向 IPC。
- `-b 1` 会死锁：可用块初值为 `blocks-1`，单块缓冲没有空块可等。上游固有行为，
  不在本次适配范围；文档化的最小可用值是 `-b 2`。
- 段名 `/buffer_<pid>` 在进程被 `SIGKILL` 时不会 `shm_unlink`（与上游 SysV 段
  在异常退出时残留同类）；正常路径（EOF/信号）都会清理。
- 上游源码仍有若干现代编译器警告（K&R 原型 64 条、`bzero` 隐式声明、一处
  `%08x` 打印指针）——均为 clang 15 下的 warning，不影响构建与运行，本次
  不做超出构建所需的改写。
