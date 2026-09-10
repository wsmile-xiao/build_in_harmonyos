# DRAFT-ohos-statx-musl-compat — OHOS musl 补 struct statx/STATX_* 宏/statx()

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-03
> **Severity**: 🟡 medium | **Category**: ohos / musl / statx / syscall / compilation

## 相关既有条目（同族差异化定位）

本 skill 与既有 "musl libc 缺失" 及 "gettext 编译期" 条目共享 OHOS musl 兼容层背景，
但本条目是 **Linux statx 系统调用接口在 OHOS musl 的整体缺失**（结构体+宏+函数）——
非重复条目；申报路径 B 时以此差异化定位为准。

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **E081**（secure_getenv） | 正式收录 | musl 无 secure_getenv（单个函数） | 非本题——那是**单个 glibc 函数**；本条目是**一整套 syscall 接口**（struct+宏+函数）且需要 syscall 包装实现 |
| **E493**（program_invocation_name） | 正式收录 | musl 无该 glibc 符号 | 非本题——那是**数据符号**；本条目是**类型/宏/函数三件套** |
| **E203**（getprogname） | 正式收录 | musl 无 getprogname | 非本题——单函数 |
| **DRAFT-ohos-gi18n-gettext-identity-macro**（polkit） | 草稿 | gettext 编译期未声明 | 非本题——那是**头文件宏**；本条目是**syscall 接口整体补全**，问题层完全不同 |

> 全库查证（2026-09-03）：`struct statx`/`STATX_TYPE`/`STATX_MNT_ID`/`statx()` 命中
> 0 条——无正面撞车；本条目为真增量。

## Scope（何时用）

在 OHOS 上编译、使用 Linux statx 接口（`statx()` 系统调用或 `struct statx` 字段）
的库时，若出现：

- `incomplete definition of type 'struct statx'`（stat-util.h 的 `statx_is_set()`
  读 `sx->stx_mask`）；
- `use of undeclared identifier 'STATX_TYPE'/'STATX_MNT_ID'/'STATX_ATTR_MOUNT_ROOT'`
  等（statx-mask/attribute-to-name.inc、mountpoint-util.c）；
- `call to undeclared function 'statx'`（recurse-dir.c 的 `statx(dir_fd, "", ...)`）。

典型实例：systemd/261（stat-util.h / recurse-dir.c / mountpoint-util.c）。

## Symptom

```text
stat-util.h:156:24: error: incomplete definition of type 'struct statx'
recurse-dir.c:179: error: call to undeclared function 'statx'
mountpoint-util.c:262: error: use of undeclared identifier 'STATX_ATTR_MOUNT_ROOT'
```

## Root Cause

1. Linux `statx()` 接口（`struct statx` + `STATX_*` 宏 + `statx()` 包装）定义在
   `linux/stat.h` / glibc 的 `sys/stat.h`；
2. OHOS musl 的 `sys/stat.h` 既不带 `linux/stat.h`（避免字段冲突），也不定义
   `struct statx` / `STATX_*` 宏，更不声明 `statx()` 函数；
3. 使用 statx 接口的库编译时分别报 incomplete type / undeclared identifier /
   undeclared function。

## Recommended Solution

**主方案：musl 兼容头补三件套。**

在 musl 兼容头（如 `src/include/musl/sys/stat.h`）补齐：

```c
#include <stdint.h>
struct statx_timestamp { int64_t tv_sec; uint32_t tv_nsec; int32_t __reserved; };
struct statx { uint32_t stx_mask; uint32_t stx_blksize; uint64_t stx_attributes;
               uint32_t stx_nlink; uint32_t stx_uid; uint32_t stx_gid;
               uint16_t stx_mode; ... uint64_t __spare3[12]; };
/* STATX_* mask（TYPE/MODE/NLINK/UID/GID/ATIME/MTIME/CTIME/INO/SIZE/BLOCKS/BTIME/
 * MNT_ID/DIOALIGN/MNT_ID_UNIQUE/SUBVOL/WRITE_ATOMIC/DIO_READ_ALIGN/ALL）+
 * attribute（COMPRESSED/IMMUTABLE/APPEND/NODUMP/ENCRYPTED/AUTOMOUNT/MOUNT_ROOT/
 * VERITY/DAX/WRITE_ATOMIC）全套宏，值取自 Linux uapi */
int statx(int dirfd, const char *pathname, int flags, unsigned int mask,
          struct statx *statxbuf);
/* 实现：syscall(__NR_statx, dirfd, pathname, flags, mask, statxbuf) */
```

注意点：`struct statx_timestamp` 必须在 `struct statx` **之前**定义（字段类型不完整
错）；宏值取自 `linux/stat.h`（systemd 自带 `src/include/uapi/linux/stat.h` 可参考）。

**回退方案**：若补全不可行，patch 源码改用 `stat()` 替代 statx 调用——改动面大且
丢失 statx 能力，不推荐。

## 单库实证

| 库 | 角色 | 结果 |
|----|------|------|
| **systemd/261** | 主验证（本 PR） | ✅ 覆盖前 stat-util.h/recurse-dir.c/mountpoint-util.c 报三类 statx 错误；补三件套后编译链接通过，conan create 通过 |

## 测试覆盖边界

- statx 兼容补全只影响 **编译期类型/宏/声明** 与 statx() 的 syscall 实现——OHOS
  内核支持 `__NR_statx`，语义与 Linux 一致；
- 声明通过率时：以 conan create 全流程（libsystemd.so.0.44.0 链接 + test_package
  R34）为实证；systemd 上游测试按 rule 1.2 平台限制声明（需运行中的 systemd 环境）。
