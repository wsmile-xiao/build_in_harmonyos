# luvit 2.18.1 适配笔记

## 项目简介
Luvit — "Node.JS for the Lua Inventor"，Lua 异步 I/O 运行时（Node.js 风格 API）。
Apache-2.0，上游 GitHub luvit/luvit。版本 2.18.1（2021-11-19 发布）。

## 架构
- **luvit**（本包）：Lua 元包，`luvit/` 源码目录含完整 deps/（Lua 模块）与 main.lua/init.lua；
- **luvi**（C 运行时）：自包含源码 `luvi-source.tar.gz`（v2.15.0）内嵌全部依赖——
  LuaJIT、libuv 1.48、lpeg、pcre2、lua-openssl、lrexlib、miniz、zlib；
- **lit**：luvi 应用（包管理器），用于 `lit make` 打包 luvit 自执行二进制。

## 鸿蒙适配要点

### 1. 内嵌 libuv 1.48 鸿蒙 patch（0001-ohos-libuv.patch）
与 main 仓库 libuv/1.52.1 的 4 个 patch 同源问题：
- `src/unix/core.c`：`uv_available_parallelism()` 用 `cpu_set_t`/`CPU_COUNT`/
  `sched_getaffinity`（鸿蒙 libc 无）→ `#if defined(__linux__) && !defined(__OHOS__)`
  走 sysconf fallback；
- `src/unix/internal.h`：`UV__CPU_AFFINITY_SUPPORTED` 条件排除 __OHOS__；
- `src/unix/thread.c`：`uv__cpu_set_t`（cpu_set_t）排除 __OHOS__；
- `src/unix/udp.c`：`uv__udp_recvmmsg/uv__udp_sendmsg` 的 mmsghdr 条件排除 __OHOS__
  （鸿蒙缺 sendmmsg/recvmmsg/struct mmsghdr）；
- `CMakeLists.txt`：`CMAKE_SYSTEM_NAME` 的 Linux 判定加 `HarmonyOS|OHOS`
  （否则 linux.c/proctitle.c 等 Linux 专属源未编译 → 链接缺 uv_uptime 等符号）。

### 2. OpenSSL 依赖
luvi 完整构建（lua-openssl 绑定）需要 OpenSSL：
- `WithSharedOpenSSL=ON` → `find_package(OpenSSL)`，用制品仓 openssl/3.5.6.1
  二进制（armv8/clang15/OHOS）注入 include/lib，避免 FetchContent 自下载
  （CI 网络风险 + openssl 源码构建复杂度）；
- requirements 显式声明 openssl/3.5.6.1。

### 3. 不自执行 zip 二进制（关键）
`luvi lit-src -- make` 产出的 lit/luvit 自执行二进制（ELF + 附加 zip）在
HMDFS 沙箱执行报 `Operation not permitted`（实测，luvi 本身可执行但自打包格式被拦截）。
**替代方案（termux 同款）**：不产出自执行二进制，bin/luvit 写启动脚本
```sh
#!/bin/sh
exec "$(dirname "$0")/luvi" "$(dirname "$0")/../share/luvit" -- "$@"
```
luvit 源码目录（share/luvit）作为 luvi 应用直接运行。
实测 `luvi <luvit-src> -- --version` → `luvit version: 2.18.1` OK。

## 验证
- 模拟 CI 干净 PATH conan create 通过；
- test_package：`luvit --version` + `luvit -e 'print(...)'`。

## 依赖
- openssl/3.5.6.1（制品仓，luvi 的 lua-openssl 绑定所需）
- LuaJIT/libuv/lpeg/pcre2/zlib：内嵌于 luvi-source（无需独立包）
