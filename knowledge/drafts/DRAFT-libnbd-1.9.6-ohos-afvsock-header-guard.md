# DRAFT：OHOS 定义 AF_VSOCK 宏但缺 `struct sockaddr_vm` 头

> Contributor: oh-executor (pc1-38) | Status: Draft | Updated: 2026-09-16
> Source: libnbd 1.9.6 首轮适配（task libnbd-1.9.6-r01-pc1-38）

## 背景

libnbd（NBD 客户端库，autotools C 库）在 HarmonyOS PC（aarch64, clang 15）上
适配时，configure 顺利通过，但编译 `lib/connect.c` 失败：

```text
lib/connect.c:176:22: error: variable has incomplete type 'struct sockaddr_vm'
  struct sockaddr_vm svm = {
                     ^
lib/connect.c:176:10: note: forward declaration of 'struct sockaddr_vm'
```

## 根因

OHOS 的 `<sys/socket.h>` **定义了 `AF_VSOCK` 常量**，但 SDK 不随附
`linux/vm_sockets.h` 或 `sys/vsock.h`，因此 `struct sockaddr_vm` 只有前向声明、
无完整定义。上游 libnbd 用 `#ifdef AF_VSOCK` 作为 vsock 支持探测：

```c
int
nbd_unlocked_aio_connect_vsock (struct nbd_handle *h,
                                uint32_t cid, uint32_t port)
{
#ifdef AF_VSOCK
  struct sockaddr_vm svm = { ... };   // ← OHOS 上类型不完整
#else
  set_error (ENOTSUP, "AF_VSOCK protocol is not supported");
  return -1;
#endif
}
```

在 Linux 完整发行版上 `AF_VSOCK` 与 `struct sockaddr_vm` 同时可用，宏探测成立；
在 OHOS 上宏存在但类型缺失，`#ifdef AF_VSOCK` 误判为可用。

## 方案（最小补丁）

把 vsock 分支守卫与 configure 的头文件检测结果绑定
（configure.ac 已 `AC_CHECK_HEADERS([linux/vm_sockets.h sys/vsock.h])`，
生成的 config.h 提供 `HAVE_LINUX_VM_SOCKETS_H` / `HAVE_SYS_VSOCK_H`）：

```c
-#ifdef AF_VSOCK
+#if defined(AF_VSOCK) && (defined(HAVE_LINUX_VM_SOCKETS_H) || defined(HAVE_SYS_VSOCK_H))
```

无头文件时进入 `#else` 分支返回 `ENOTSUP`，API 保持完整。

## 验证

- 补丁后 `make` 全绿；上游 `make check`：12 PASS / 1 SKIP(dlopen, 静态构建无 .so.0) / 0 FAIL
- `conan create`（OHOS profile）通过，test_package 2/2 通过

## 适用边界

- 适用：所有在 OHOS / 裁剪内核头环境下使用 AF_VSOCK 的 C/C++ 库
- 反例：Linux 完整发行版有 vm_sockets.h，无需该守卫；若 OHOS SDK 未来补齐头文件，守卫自动放开
- 可复用性：跨库可复用（NBD/qemu/libvirt 等 vsock 客户端代码同此模式）

## 查重

- knowledge/graph/、doc/、drafts/ 均无 vsock/sockaddr_vm 条目 → 未命中
- 关系：无 similar / caused_by / prerequisite_of / conflicts_with 条目
