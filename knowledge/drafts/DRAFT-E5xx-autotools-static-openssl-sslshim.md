# DRAFT: autotools 静态 openssl 的 SSL shim 适配模式

## 场景

autotools 软件（探测式 `--with-ssl` configure，如 nagios/nrpe/nsca 类监控组件）接入 conan 静态 openssl 包时的两个连环坑。

## 症状

```
checking for SSL headers... found in <conan>/include/..
checking for SSL libraries... configure: error: Cannot find ssl libraries
```
或（绕过头文件问题后）：
```
conftest.c:70:10: fatal error: 'openssl/ssl.h' file not found
```
或（链接期）：
```
ld.lld: error: unable to find library -lssl
```

## 根因（两层）

1. **头文件探测分支陷阱**：configure 依次探测 `$dir/include/$SSL_INC_PREFIX/$SSL_HDR`、`$dir/include/$SSL_HDR`、`$dir/$SSL_HDR`。`--with-ssl-inc=<openssl>/include` 时命中第一分支（`include/openssl/ssl.h` 存在）→ CFLAGS 加 `-I<openssl>/include/openssl` 且 `SSL_INC_PREFIX="openssl/"` → conftest 的 `#include <openssl/ssl.h>` 变成找 `<openssl>/include/openssl/openssl/ssl.h`（双层拼接）→ 编译失败。
2. **库后缀探测**：configure 用 `soext="so"` 只探测 `libssl.so`；conan openssl 默认静态（`.a`）→ "Cannot find ssl libraries"。

## 方案：SSL shim 目录

```
shim/
├── include/
│   ├── ssl.h          # 一行转发: #include <openssl/ssl.h>
│   └── openssl -> <conan_openssl>/include/openssl   # 软链
└── lib/
    ├── libssl.so -> <conan_openssl>/lib/libssl.a     # 软链
    └── libcrypto.so -> <conan_openssl>/lib/libcrypto.a
```

configure 参数：
```
--with-ssl=<shim> --with-ssl-inc=<shim>/include --with-ssl-lib=<shim>/lib
```

原理：
- 头文件：`shim/include/ssl.h` 存在 → 命中 `$dir/include/$SSL_HDR` 分支 → `SSL_INC_PREFIX=""`，CFLAGS 加 `-I shim/include` → conftest `#include <ssl.h>` → 转发头 → `#include <openssl/ssl.h>` → 同前缀下 `openssl/` 软链解析到真实头。
- 库：`.so` 软链满足 soext 探测；链接行保持 `-lssl -lcrypto`，ld 解析符号链接到 `.a`，最终二进制静态自包含（守护进程无运行时库路径依赖）。

## fallback

若上游 conan openssl 提供 `.so` 变体（shared 构建或选项开启），直接 `--with-ssl-inc=$OPENSSL_DIR/include` 即可，无需 shim。

## 验证

nagios/4.5.14 本地 conan create 全绿（G1-G4 + L2/L4/L5），daemon/CGI 全部静态链接 openssl。
