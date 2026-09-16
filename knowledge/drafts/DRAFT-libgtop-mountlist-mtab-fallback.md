# DRAFT-libgtop-mountlist-mtab-fallback — OHOS/容器无 /etc/mtab 时 mountlist 为空：setmntent 回退 /proc/self/mounts

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-09
> **Severity**: 🟡 medium | **Category**: mountlist / /etc/mtab / /proc/self/mounts / filesystem / OHOS / containers

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **E237**（acpid ACPI） | 正式收录 | /proc/acpi、/sys/bus/acpi 等内核接口缺失 | 非本题——E237 是 ACPI 事件接口；本题是挂载表 /etc/mtab 缺失 |

> index.tsv 查证（2026-09-09）：`/etc/mtab` 命中 0 条、`setmntent` 命中 0 条、
> `mountlist` 命中 0 条、`/proc/self/mounts` 命中 0 条——无正面撞车。

## Scope（何时用）

在 OHOS 或精简容器（只读 rootfs、无 `/etc/mtab`）上编译运行任何读取挂载表
的软件（libgtop 的 glibtop_get_mountlist、类 `mount` 工具）时，若出现：

- 运行期 `glibtop(c=N): [WARNING] Could not open /etc/mtab: No such file or directory`；
- `glibtop_get_mountlist` 返回 `number=0`（空挂载表），fsusage/disk 统计静默为空；
- 已确认 `/proc/self/mounts` 存在且可读（内核运行时挂载表）。

## Symptom

```text
glibtop(c=29991): [WARNING] Could not open /etc/mtab: No such file or directory
OHOS test FAIL: mountlist empty or NULL (number=0,0)
# 上游示例 mountlist 同样 0 个 Mount_Entry（rc=0 但不输出任何挂载点）
```

## Root Cause

libgtop linux sysdeps 的 `sysdeps/linux/mountlist.c` 用
`setmntent(MOUNTED, "r")` 读取挂载表，MOUNTED 在无 mtab 系统上解析为
`/etc/mtab`；OHOS/容器不提供该文件（现代内核挂载表在 `/proc/self/mounts`），
open 失败 → 仅 warn 后返回 0 挂载点，所有依赖 mountlist 的调用静默为空，
且不报错，难以察觉。

## Solution

源码补丁（archives/l/libgtop/2.41.3/patches/0002-mountlist-proc-self-mounts.patch）：

```c
if (!(fp = setmntent(MOUNTED, "r"))) {
    /* OHOS / containers lack /etc/mtab; fall back to the runtime
       mount table which is always present. */
    fp = setmntent("/proc/self/mounts", "r");
}
if (!fp) {
    glibtop_warn_io_r(server, "Could not open mount table");
    goto out;
}
```

要点：先试 MOUNTED（保持常规 Linux 行为），失败后回退 `/proc/self/mounts`
（Linux 2.4.19+ 始终存在，反映真实挂载）；两次都失败才报错返回。

## Verification

```bash
cd archives/l/libgtop/2.41.3
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# test_package 鸿蒙专项测试：mountlist 139 mounts (first=/)
```

## 适用边界 / 反例

- 常规 Linux（有 /etc/mtab）行为不变——先试 MOUNTED 成功即用原路径；
- /proc 不可挂载的极端环境（chroot 无 /proc）两次打开都失败 → 仍报错返回，
  不伪造数据；
- 该回退是通用 POSIX 语义（glibc `mount` 工具同样优先 /proc/self/mounts）。

## 关系字段

- similar_to: E237（同为 /proc 语义，非挂载表）
- caused_by: OHOS/容器无 /etc/mtab
- conflicts_with: 无