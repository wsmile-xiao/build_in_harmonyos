# DRAFT-socket-wrapper-musl-lfs64-mmsg-ohos — musl/OHOS 下 LD_PRELOAD 库的 LFS64 宏重定义、mmsg 原型冲突与 DT_SONAME 丢失

> **Contributor**: socket-wrapper adaptation task | **Status**: DRAFT | **Updated**: 2026-09-02
> **Severity**: 3 (high) | **Category**: toolchain / musl / libc / portability / cmake / ohos
> **Scope**: socket-wrapper/1.5.2（cwrap 家族 LD_PRELOAD 库在 OHOS PC 设备上的适配）

## 问题（Symptom）

socket_wrapper 1.5.2（CMake，cwrap 家族 socket 劫持库）在 OHOS PC 设备上用 ohos-aarch64 Conan profile 构建时出现三类错误：

1. **编译错误（重定义）**：
   ```text
   error: redefinition of 'fopen'   (stdio.h: fopen64 宏展开)
   error: redefinition of 'open'    (fcntl.h: open64 宏展开)
   error: redefinition of 'openat'  (fcntl.h: openat64 宏展开)
   ```
2. **编译错误（原型冲突）**：
   ```text
   error: conflicting types for 'recvmmsg'
   note: previous declaration is here (sys/socket.h:75)
   error: conflicting types for 'sendmmsg'
   note: previous declaration is here (sys/socket.h:74)
   ```
3. **质量门禁 L5a 失败（打包后）**：
   ```text
   [fail] L5a: libsocket_wrapper.so 缺少 DT_SONAME — 下游链接器无法按 SONAME 寻址
   ```

## 根因（Root Cause）

三个独立的 musl/OHOS 平台差异：

1. **LFS64 宏别名**：musl 在 `_GNU_SOURCE` 下将 `fopen64`/`open64`/`openat64` 定义为指向 `fopen`/`open`/`openat` 的宏（stdio.h:211 / fcntl.h:204-206）。上游代码定义 `FILE *fopen64(const char *name, const char *mode)` 拦截函数时，函数名被宏展开成 `fopen`，与前面已定义的 `fopen` 拦截函数冲突。
2. **mmsg 原型差异**：musl 声明 `int recvmmsg(int, struct mmsghdr *, unsigned int /*vlen*/, unsigned int /*flags*/, struct timespec *)` 和 `int sendmmsg(int, struct mmsghdr *, unsigned int, unsigned int)`——flags 是 `unsigned int`。上游只实现了 glibc（`int` flags，三个分支）和 FreeBSD（`ssize_t` 返回值）原型链。
3. **HarmonyOS host 平台识别**：OHOS 适配版 Conan 生成的工具链不设置 `CMAKE_SYSTEM_NAME`，CMake 4.1.2 在设备上探测到 host 为 `HarmonyOS`（`CMAKE_CROSSCOMPILING=FALSE`）。"HarmonyOS" 不在 CMake 已知平台列表中 → `CMAKE_SHARED_LIBRARY_SONAME_FLAG` 为空 → 版本化共享库链接命令缺少 `-Wl,-soname` → 打包产物无 DT_SONAME、无 `.so.0`/`.so.0.5.2` 版本化布局。

## 方案（Recovery）

对应三个修复（见 archives/s/socket-wrapper/1.5.2/patches/0001-0003 与 conanfile.py）：

```c
/* 0001: LFS64 宏在拦截定义前展开 */
#ifdef __OHOS__
#undef fopen64   /* open64/openat64 同理 */
#endif
FILE *fopen64(const char *name, const char *mode) { ... }
```

```cmake
# 0002/0003: musl 原型探测（ConfigureChecks.cmake + config.h.cmake）
check_prototype_definition(recvmmsg
    "int recvmmsg(int __fd, struct mmsghdr *__vmessages, unsigned int __vlen, unsigned int __flags, struct timespec *__tmo)"
    "-1" "sys/types.h;sys/socket.h" HAVE_RECVMMSG_UNSIGNED_FLAGS)
check_prototype_definition(sendmmsg
    "int sendmmsg(int __fd, struct mmsghdr *__vmessages, unsigned int __vlen, unsigned int __flags)"
    "-1" "sys/types.h;sys/socket.h" HAVE_SENDMMSG_UNSIGNED_FLAGS)
```

```python
# conanfile.py generate(): 显式声明 OHOS 平台恢复 soname
if str(self.settings.os) == "OHOS":
    tc.cache_variables["CMAKE_SYSTEM_NAME"] = "OHOS"
    tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
```

## 验证（Evidence）

- 修复后 `conan create`：上游 CTest 29/29 注册测试 100% 通过；test_package LD_PRELOAD 回环重定向通过。
- `llvm-readelf -d libsocket_wrapper.so` → `SONAME [libsocket_wrapper.so.0]`；`lib/` 呈现 `.so → .so.0 → .so.0.5.2` 版本化布局。
- W3 本地 CI：`L0/L1/L4/L5 = pass`，`JC_RESULT=pass`，Pass rate 100%。
- 日志：`archives/s/socket-wrapper/1.5.2/reports/w3-local-ci.log`

## 关联

- 同家族先例：pam-wrapper/1.1.8（ELF 签名 + LD_PRELOAD 测试）、nss-wrapper/1.1.16（NSS ABI 补丁 + shadow 能力门控）
- 上游 tag `socket_wrapper-1.5.2`（非 v1.5.2），gitlab archive URL：`https://gitlab.com/cwrap/socket_wrapper/-/archive/socket_wrapper-1.5.2/socket_wrapper-socket_wrapper-1.5.2.tar.gz`
