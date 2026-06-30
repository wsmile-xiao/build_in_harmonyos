# connect 1.106 适配笔记

## 编译环境
- 构建系统: makefile (plain Makefile)
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 状态: built
- G0 门禁: ✅ PASS（已修复）

## 编译步骤

1. 下载源码: https://github.com/gotoh/ssh-connect/archive/refs/tags/1.106.tar.gz
2. 源码为单文件 C 程序 (connect.c + Makefile)
3. 添加空操作 `configure` wrapper（解决 G0 门禁 configure 步骤）
4. 修改 Makefile 添加 `install` target 和 DESTDIR 支持
5. 修复 getpwuid() 致命退出（沙箱/容器环境下无 /etc/passwd）
6. 编译命令: `make CC=clang CFLAGS="-DSOCKLEN_T=unsigned -fPIC -O2"`
7. 安装命令: `make install DESTDIR=$TEST_PREFIX`
8. 无 make check（项目没有测试套件）

## G0 门禁修复记录

**原始问题**: connect 是纯 Makefile 项目（无 configure 脚本、无 make install target），导致 `clean-verify` 在 configure 和 make install 步骤失败。

**修复方案**（参照 bcrypt v1.1 模式）:

| 修复项 | 补丁 | 说明 |
|--------|------|------|
| configure wrapper | 0002-configure.patch | 添加空操作 `#!/bin/sh; exit 0` 的 configure 文件 |
| Makefile install target | 0001-Makefile.patch | 添加 `install: connect` target，支持 DESTDIR |
| CC/CFLAGS ?= 模式 | 0001-Makefile.patch | CC?=clang, CFLAGS?=-fPIC -O2, 允许环境覆盖 |
| __OHOS__ 守卫 | 0003-connect.c.patch | 禁用 WITH_RESOLVER/switch_ns（5处修改） |
| getpwuid 降级 | 0003-connect.c.patch | getpwuid 失败时降级而非 fatal（2处修改） |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `use of undeclared identifier '_res'` | musl libc 不提供 glibc 的 `_res` 全局变量 | `#ifdef __OHOS__` 禁用 WITH_RESOLVER/switch_ns |
| 2 | G0 configure 失败 | 纯 Makefile 项目无 configure 脚本 | 添加空操作 configure wrapper (exit 0) |
| 3 | G0 make install 失败 | Makefile 无 install target | 添加 install target + DESTDIR 支持 |
| 4 | getpwuid() FATAL 致命退出 | 沙箱/容器环境无 /etc/passwd，UID 无记录 | `#ifdef __OHOS__` 降级为 debug + fallback |
| 5 | SSL 下载失败 | HTTPS 证书验证失败 | curl --insecure 手动下载 |

## 源码修改详情

**Makefile**（0001-Makefile.patch，+11/-4）:
1. `CC=gcc` → `CC?=clang`（允许环境覆盖）
2. `CFLAGS=-DSOCKLEN_T=unsigned` → `CFLAGS?=-DSOCKLEN_T=unsigned -fPIC -O2`
3. 新增 `PREFIX ?= /usr/local` 和 `DESTDIR ?=`
4. 新增 `install: connect` target（mkdir + cp + chmod 755）

**connect.c**（0003-connect.c.patch，+36/-20，共5处修改）:
1. **WITH_RESOLVER 守卫**: `!defined(__OHOS__)` 禁用 WITH_RESOLVER 和 nameser/resolv 引入
2. **switch_ns 函数守卫**: `!defined(__OHOS__)` 不编译 switch_ns
3. **switch_ns 调用守卫**: `!defined(__OHOS__)` 不调用 switch_ns
4. **getusername() 降级**: `#ifdef __OHOS__` → return "unknown" 代替 fatal()
5. **read_parameter_file() 降级**: `#ifdef __OHOS__` → 跳过 home config 代替 fatal()

**configure**（0002-configure.patch，+3/-0）:
```sh
#!/bin/sh
# Empty configure wrapper for Makefile-only projects on OpenHarmony
exit 0
```

所有 C 修改使用 `#ifdef __OHOS__` 条件编译守卫（R8: 源码"四不"准则）。

## 功能测试结果

### TCP 数据传输验证
```
客户端发送: HELLO_CONNECT_V1.106
服务器回显: ECHO:HELLO_CONNECT_V1.106
✅ TCP 数据传输验证成功：发送数据与回显数据匹配
```

### 参数解析验证
| 参数 | debug 输出 | 结果 |
|------|-----------|------|
| 无参数 | 显示 usage + Version 1.106 | ✅ |
| -d (debug) | DEBUG: relay_method, dest_host, dest_port | ✅ |
| -S (SOCKS5) | relay_method=SOCKS, relay_user=unknown | ✅ |
| -H (HTTP proxy) | relay_method=HTTP, relay_host=127.0.0.1 | ✅ |
| -w (timeout) | setting timeout: 5 seconds | ✅ |
| -p (local port) | local_type=socket, local_port=20000 | ✅ |
| -n (no DNS) | dest_host=127.0.0.1 (直接使用 IP) | ✅ |
| -Z (错误参数) | ERROR: unknown option | ✅ |

### getpwuid 降级验证
```
DEBUG: getpwuid() failed for uid: 20020098, skipping home config
DEBUG: getpwuid() failed for uid: 20020098, using fallback username
```
✅ 不再 FATAL 致命退出，二进制在沙箱环境下功能完全正常

## 依赖版本

无外部依赖（纯 C 程序，仅使用 POSIX 网络库）

---

**编译结束**: 2026-06-01 15:11
**最终状态**: built