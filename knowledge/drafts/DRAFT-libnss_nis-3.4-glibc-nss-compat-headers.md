# DRAFT-libnss_nis-3.4 — glibc NSS 专有头在 OHOS/musl 的树内最小兼容头方案

## 错误面

- **触发**：clang/make/configure/conan
- **阶段**：compilation / configuration
- **签名**：`fatal error: 'nss.h' file not found` /
  `fatal error: 'aliases.h' file not found` /
  `fatal error: 'rpc/netdb.h' file not found` /
  `use of undeclared identifier 'NETDB_INTERNAL'` /
  `incomplete type 'struct gaih_addrtuple'` /
  `symbol not found: __mempcpy`

## 识别

- severity: 2（🟡medium，编译期可定位，但 glibc 专有头依赖面广）
- category: musl, libc, portability, compat, ohos, headers, nss

## 诊断

libnss_nis 是 glibc **NSS（Name Service Switch）模块**：实现 `_nss_nis_*_r`
入口，由 glibc NSS 框架 dlopen("libnss_nis.so.2") 加载。源码（nis-*.c 等
10+ 文件）无条件 include glibc 专有头：

| 缺失头 | 内容 | 本库使用 |
|--------|------|---------|
| `<nss.h>` | `enum nss_status` + `NSS_STATUS_*` 五常量 | 122 处返回/比较 |
| `<aliases.h>` | `struct aliasent` | nis-alias.c（alias_name/alias_members/...） |
| `<rpc/netdb.h>` | rpc 数据库 API 声明 | nis-rpc.c（仅需 struct rpcent） |

OHOS 用 musl libc：无 NSS 框架，不提供这些头；且连带缺失：

- `NETDB_INTERNAL` 宏（musl netdb.h 无 glibc 枚举）
- `struct gaih_addrtuple`（`_nss_nis_gethostbyname4_r` NSS 接口参数，
  布局在 glibc inet/getaddrinfo.h）
- `__mempcpy`（glibc 内部符号别名，musl 只导出 `mempcpy()`）

## 方案

在源码树 `src/` 下新增三个**最小兼容声明头**（非复制 glibc 头），利用
`src/Makefile.am` 的 `AM_CPPFLAGS = -I$(srcdir)` 让 `#include <nss.h>` 等
自然解析到树内文件：

1. `src/nss.h`：
   - `enum nss_status { NSS_STATUS_TRYAGAIN=-2, NSS_STATUS_UNAVAIL,
     NSS_STATUS_NOTFOUND, NSS_STATUS_SUCCESS, NSS_STATUS_RETURN }`
     （对齐 glibc nss/nss.h 常量序）
   - `NETDB_INTERNAL=-1` / `NETDB_SUCCESS=0`（#ifndef 保护）
   - `struct gaih_addrtuple { next, name, family, addr[4], scopeid }`
     （对齐 glibc inet/getaddrinfo.h 布局）
   - `#define __mempcpy mempcpy`（nis-pwd.c 4 处调用）
2. `src/aliases.h`：`struct aliasent { alias_name, alias_members,
   alias_members_len, alias_local }`（对齐 glibc inet/aliases.h）
3. `src/rpc/netdb.h`：仅 `#include <rpc/rpcent.h>`（rpc 模块只需
   struct rpcent，由 libtirpc 提供）

不修改任何 .c 文件；补丁文件带 patch_description 说明（R8 平台兼容例外）。

参考补丁：`archives/l/libnss_nis/3.4/patches/0001-ohos-glibc-compat-headers.patch`

## 验证（libnss_nis 3.4 OHOS aarch64 实测）

- make：PASS（含兼容头补丁）
- make check（上游 nss_loader-test）：1/1 PASS
  （dlopen libnss_nis.so.2 + dlsym _nss_nis_getpwnam_r）
- conan create / conan-verify G0-G4：全 PASS
- 消费者测试（test_package/test.c）：dlopen + dlsym + **实际调用**
  `_nss_nis_getpwnam_r` → OHOS 无 NIS 域，断言返回 NSS_STATUS_UNAVAIL → PASS

## 边界 / 反例

- **不冲突 E194**：E194 forbid "复制 glibc 头文件到 musl"（会 ABI 不兼容）；
  本方案是**树内最小声明头**（仅本库编译可见），不进入系统 include，
  是"声明所需最小类型"而非"复制 glibc 实现"。
- **NSS 模块配套**：配方 `package_info.includedirs = []`（无公共头，
  E498 覆盖）；默认 `shared=True`（dlopen 消费，同 nss-wrapper）。
- 反例：如果库只在 glibc 平台消费（如纯 Linux glibc 分发），无需此方案；
  若库有自带的 NSS 兼容层（如 nss-wrapper 的 NSS_WRAPPER_PROVIDE_STATUS_ENUM
  CMake 探测），优先用上游机制而非补头。

## 适用边界

- 任何 `libnss_*` 家族 / NSS 模块 / 直接引用 `nss_status`、`NSS_STATUS_*`、
  `<nss.h>`、`<aliases.h>` 的库迁移到 OHOS/musl
- gethostbyname4_r 风格 NSS 接口的 `struct gaih_addrtuple` 缺失
- glibc 内部符号（`__mempcpy` 等）在 musl 的宏映射

## 查重摘要

| 轴 | 结果 |
|----|------|
| exact_duplicate | false（无完整重复条目） |
| causal_duplicate | false（E544 是 netdb 宏缺项，本条是 NSS 框架头整体缺失） |
| trigger_overlap | partial（NETDB_INTERNAL 触发面与 E544-draft 重叠） |
| solution_overlap | partial（E544 用 #ifndef fallback；本条树内完整声明头 + 符号映射） |
| combination_novelty | true（nss.h+aliases.h+rpc/netdb.h+gaih_addrtuple+__mempcpy 组合） |
| boundary_novelty | true（树内最小声明 ≠ 复制 glibc 头的边界） |
| test_migration_novelty | true（消费者 dlopen+实际调用断言 NSS_STATUS_UNAVAIL） |

关系: `similar_to`=E544-draft、E194；`caused_by`=musl 无 glibc NSS 基础设施；
`prerequisite_of`=libnss_nis 系列模块；`conflicts_with`=E194 forbid
（仅当复制 glibc 头时冲突，本方案守界）。
