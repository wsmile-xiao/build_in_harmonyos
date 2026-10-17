# moarvm 2025.11 适配笔记

## 编译环境

- 构建系统: custom（Perl Configure.pl + make）
- 编译日期: 2026-08-19
- 编译器: clang/clang++
- 平台: HarmonyOS PC aarch64
- 状态: built

## 编译步骤

```bash
perl Configure.pl --os=linux --compiler=clang --cc=clang --ld=clang --ar=llvm-ar --relocatable --prefix=<prefix>
make -j1
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接 `moar` 时缺少 `pthread_getaffinity_np` 和 `pthread_setaffinity_np` | OHOS musl 不提供 GNU pthread 亲和性扩展，内置 libuv 默认走 Linux pthread 分支 | 为 `__OHOS__` 选择 libuv 的 `sched_getaffinity`/`sched_setaffinity` 分支（E211） |
| 2 | 自动初始化器将 `3rdparty/cmp` 误判为嵌套源码根 | release tarball 包含多个嵌入式第三方项目 | 依据官方 tarball 顶层 `MoarVM-2025.11/` 手动验证源码结构 |

## 源码修改

- `0001-libuv-ohos-affinity.patch`: 为内置 libuv 的线程亲和性实现添加 `__OHOS__` 分支。

## 依赖版本

无外部 Conan 依赖；官方 release tarball 已包含所需第三方源码。

## 验证结果

探索构建可稳定复现亲和性链接失败；应用补丁后，Conan 构建执行上游 `make test`，消费测试执行 `moar` CLI 冒烟检查及 libuv 线程亲和性设置、查询、恢复往返验证。

## 注意事项

MoarVM 同时安装 `bin/moar`、`lib/libmoar.so`、头文件和 NQP MAST 资源，因此配方同时声明 bindirs、libdirs 与 includedirs。`test_affinity.c` 直接链接打包后的 `libmoar.so`，覆盖本次补丁修改的内置 libuv 亲和性路径。
---

**编译结束**: 2026-08-19 08:53
**最终状态**: built
