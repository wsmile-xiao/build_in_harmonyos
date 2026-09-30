# ndppd 0.2.6 OHOS 适配：strerror_r musl 语义、Makefile man 页硬编码 gzip、WITH_ND_NETLINK 规避

> 对应结构化条目：`ndppd-0.2.6-ohos-makefile-daemon-portability.kv`（同 stem 成对）

## 现象

1. OHOS SDK clang++ 交叉编译 ndppd 0.2.6（tag tarball）时：
   ```
   src/logger.cc:92:12: error: no viable conversion from returned value of type 'int' to 'std::string'
       return strerror_r(errno, buf, sizeof(buf));
   ```
2. `make all`（默认目标）失败：`/bin/gzip: No such file or directory`（构建 man 页）。
3. 若强行启用 `WITH_ND_NETLINK`：链接 `pthread_cancel` 失败（musl 无此符号，E085/E127）。
4. 运行 `ndppd -v ...` 输出 `version 0.2.4`，与包版本 0.2.6 不一致。

## 根因

### 1. strerror_r 的 glibc/musl 语义差（核心）

`strerror_r` 在 glibc 有两个签名：`_GNU_SOURCE` 下返回 `char*`（GNU 扩展），否则返回 `int`（POSIX）。
**musl（含 OHOS）永远只有 POSIX `int` 签名**——即使 `_GNU_SOURCE` 已定义也不会切换。
OHOS sysroot 的 features.h 默认开启 `_GNU_SOURCE`，于是 ndppd 原有的
`#if (_POSIX_C_SOURCE >= 200112L ...) && ! _GNU_SOURCE` 判定必然走 GNU 分支 → 编译错误。
特征宏（`_GNU_SOURCE`/`_POSIX_C_SOURCE`）在两个平台都为真，**无法**用来区分实现；必须用 `__GLIBC__`。

### 2. Makefile `all` 目标硬编码 `/bin/gzip`

```
GZIP ?= /bin/gzip
all: ndppd ndppd.1.gz ndppd.conf.5.gz
ndppd.1.gz: ${GZIP} < ndppd.1 > ndppd.1.gz
```
OHOS 无 `/bin/gzip`。但二进制目标 `ndppd` 不依赖 man 页 → 只构建该目标即可。

### 3. WITH_ND_NETLINK 可选路径含 musl 禁用 API

`src/nd-netlink.cc`（仅 `WITH_ND_NETLINK=1` 时编译）使用 `pthread_cancel` + libnl + glib。
上游已在 `ndppd.cc`/`rule.cc`/`proxy.cc` 用 `#ifdef WITH_ND_NETLINK` 保护所有调用点，
默认路径（解析 `/proc/net/ipv6_route` + 标准 ioctl/poll）零外部依赖、musl 全兼容。

### 4. 版本宏滞后

上游 0.2.6 tag 中 `src/ndppd.h` 仍为 `#define NDPPD_VERSION "0.2.4"`。测试断言必须匹配 0.2.4，
并在 notes/manifest 记录，避免 CI 断言 0.2.6 失败。

## 解决方案

| # | 问题 | 方案 |
|---|------|------|
| 1 | strerror_r 语义 | 补丁：`logger::err()` 改按 `#ifdef __GLIBC__` 分支（glibc→char* 直接返回；musl→POSIX int 判非零） |
| 2 | /bin/gzip | conanfile 只跑 `make ndppd CXX=clang++ CXXFLAGS="-O2 -fPIC -Wall"`；package 用 copy() 装 bin/licenses/res |
| 3 | pthread_cancel/libnl | 不启用 WITH_ND_NETLINK（上游 #ifdef 已保护，无需补丁） |
| 4 | 版本串 | test 断言 grep "version 0.2.4"，差异记录进 notes.md/manifest.yaml |

## 验证

- 本机（DevEco OHOS SDK）`--target=aarch64-linux-ohos` 交叉编译 9/9 源文件 + 链接 PASS，
  产物 AArch64 DYN ELF（PIE）。
- 补丁 `git apply --check` 对官方 tarball 干净应用。
- `lang-preflight`（cpp/cpp）与 `prescan` 通过（prescan 命中的 PSCAN-MUSL-001 即被规避的
  nd-netlink.cc；PSCAN-GLIBC-001 即本补丁自身）。

## 踩坑提示（给后来者）

- musl 下见到「明明定义了 `_GNU_SOURCE` 还走错分支」不要去调 feature 宏——musl 根本不认，
  直接换成 `__GLIBC__` 判定。
- Makefile 型守护进程先看 `all` 目标是否绑定了宿主专属工具（gzip/install/chown 等），
  能拆出纯二进制目标就别动 Makefile。
- 断言版本号前先 grep 源码里的版本宏，别信 tag 名（ndppd 0.2.6 报 0.2.4）。
