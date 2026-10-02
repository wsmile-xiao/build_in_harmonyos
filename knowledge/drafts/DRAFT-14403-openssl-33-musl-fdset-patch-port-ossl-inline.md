# DRAFT-14403：3.5.x musl FD_SET 补丁移植 3.3.0 失败（ossl_inline）

## 适用场景
把 openssl/3.5.8.1 配方（含 -D__MUSL__ + FD_SET 有界补丁）向 OpenSSL 3.3.x
源码树平移时；或任何跨 OpenSSL 大版本移植 internal 头文件补丁时。

## 报错签名（命中任一即适用）
```
include/internal/sockets.h:212:8: error: unknown type name 'ossl_inline'
static ossl_inline void openssl_fdset(int fd, fd_set *set)
include/internal/sockets.h:215:9: warning: call to undeclared library function 'abort'
```

## 根因
3.5.x 的 0002-include-internal-sockets.h 补丁在 sockets.h 增加
`__MUSL__` 分支的 `static ossl_inline openssl_fdset` 有界实现，依赖
`ossl_inline` 宏（定义于 internal/macro.h）。OpenSSL 3.5.x 的 sockets.h
已包含 macro.h，3.3.0 的 sockets.h **未包含**——版本间头文件包含链变化，
补丁平移后 `__MUSL__` 分支首次参与编译即失败。

附带实测结论：3.3.0 在 `--with-rand-seed=getrandom` 下 configdata 0 次
DEVRANDOM 出现（完全排除），其余 FD_SET 使用（speed.c job 调度）在 OHOS
SDK 链接无虞（make test 3185 项全跑 0 链接错误）——3.3.0 场景下
-D__MUSL__ + 有界补丁整体不需要。

## 修法
1. 跨 OpenSSL 大版本移植补丁前，先 diff 目标版本头文件包含链
   （internal/sockets.h、internal/macro.h），不假设可平移
2. 3.3.x 配方：保留 --with-rand-seed=getrandom（E235 等效手段），
   不加 -D__MUSL__、不带 FD_SET 补丁；补丁机制保留 no-op 过 G1
3. 若 3.3.x 实测出现 __fd_chk 链接错误（当前未出现）：优先修 rand 源选择，
   避免全局 -D__MUSL__（宏面大，易引入此类头文件依赖问题）

## 验证
- 带 -D__MUSL__ + 移植补丁：make build_sw 失败（2026-09-29 实测）
- 去宏去补丁：conan-verify G2 PASS + make test Result: PASS（2026-09-29 实测）
