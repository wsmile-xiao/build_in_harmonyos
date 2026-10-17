# DRAFT: musl 不从 <sys/file.h> 传递引入 <fcntl.h> —— O_CREAT/O_RDWR 报 undeclared identifier

> 草稿条目：`DRAFT-libsecret-0218-musl-sysfile-fcntl-transitive-include`
> 触发事件：libsecret 0.21.8 适配（2026-09-20），conan-verify G2 首跑失败

## 现象

```
../libsecret/secret-file-collection.c:836:26: error: use of undeclared identifier 'O_CREAT'
../libsecret/secret-file-collection.c:836:36: error: use of undeclared identifier 'O_RDWR'
```

同一份源码在 Linux/glibc 上编译通过，在 OHOS（musl libc）上报错。

## 根因

- glibc 的 `<sys/file.h>` 内部 `#include <fcntl.h>`，所以"为了 `flock()` 只包含 `<sys/file.h>`"
  的代码在 glibc 上顺手就能用 `O_CREAT/O_RDWR` 等 open 标志。
- musl 的 `<sys/file.h>` 不传递引入 `<fcntl.h>`（POSIX 也不保证），OHOS clang 严格按可见声明编译。
- libsecret 0.21.8 新增的 flock 键环锁
  （`g_open(lock_path, O_CREAT|O_RDWR, 0600)` + `flock(fd, LOCK_EX)`）踩中此坑。

## 修复

在使用 open 标志的源文件补一行：

```c
#include <sys/file.h>
#include <fcntl.h>   /* O_CREAT/O_RDWR — musl 不从 sys/file.h 传递引入 */
```

- 纯可移植性修复：Linux 上同样正确，可上游提交。
- **禁止**用 `#ifdef __OHOS__` 守卫（R8/PF5）。
- 实测：libsecret 0.21.8 补丁 `0002-libsecret-secret-file-collection.c.patch`（+1 行），
  conan-verify G2 复跑全绿，file-collection 测试（含并发写锁）通过。

## 识别要点

| 信号 | 判据 |
|---|---|
| 错误文本 | `use of undeclared identifier 'O_CREAT'`（及 O_RDWR/O_RDONLY/O_WRONLY/O_TRUNC） |
| 源码特征 | 同时使用 flock 与 open 标志，只有 `#include <sys/file.h>` 没有 `<fcntl.h>` |
| 快速验证 | `grep -n 'O_CREAT' <file>` 命中且 `grep -n '#include <fcntl.h>' <file>` 为空 |

## 同类风险面

凡是"在 glibc 上靠传递包含碰巧编译过"的头文件组合都有此风险：`<sys/mount.h>`、
`<sys/stat.h>` 与其他标志宏的组合等。交叉到 musl 平台时，缺哪个补哪个，一律不用平台宏。
