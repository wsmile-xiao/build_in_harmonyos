# stb_ds 0.67 适配笔记

## 编译环境
- 构建系统: header-only（单头文件库，无构建系统）
- 编译日期: 2026-08-31
- 编译器: clang/clang++ (ohos-aarch64 profile)
- 状态: built（本地 W3 验证通过，CI 未 upload）

## 编译步骤

stb_ds 为单头文件库（stb_ds.h，v0.67 = commit 2c980bb59875b0d32144a71867fbdebb2f77cd20），
无独立构建系统。Conan 配方采用 header-only 模式：

1. `conan create`（ohos-aarch64 profile）：get() 下载官方 tarball → strip_root=True 解压 → package() 拷贝 stb_ds.h 到 include/、LICENSE 到 licenses/
2. test_package 编译运行上游测试：
   - `./test_ds`（test_ds.c，C++ 模式编译，DS_TEST：STBDS_UNIT_TESTS + STBDS_SMALL_BUCKET + 8 组 churn）→ "Ok!" exit 0
   - `./test_ds_cpp`（test_ds_cpp.cpp，C++，DS_TEST：STBDS_UNIT_TESTS + 8 组 churn）→ "Ok!" exit 0
   - `./test_ds_stats`（test_ds.c，DS_STATS：STBDS_STATISTICS 探针统计 8 组 500000 项）→ exit 0
   - `./test_stb_ds`（消费者测试：arrput/hmput/shput 等 API 调用）→ "test stb_ds 0.67: OK"

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | test_ds.c 在 clang **C** 模式编译报数组 key 错误 | 上游 stb_ds.h 的 STBDS_ADDRESSOF 宏在 clang C 模式（literal array 路径）下对数组 key 有固有限制，上游注释自认 "currently broken for clang"（MSVC/gcc 走 `&(value)` 分支） | test_ds.c 以 **C++ 模式**编译（CMake `set_source_files_properties(LANGUAGE CXX)`），编译运行全部通过；stb_ds 官方声明支持 C++ |
| 2 | test_ds.c DS_STATS 分支编译缺 printf 声明 | 上游 C 编译依赖隐式声明 | test_package 副本补 `#include <stdio.h>` |
| 3 | conan create 打包后 include 路径不存在 | conan 2 的 `get()` 默认 `strip_root=False`，GitHub archive 保留顶层目录 `stb-2c980bb.../` | `get(..., strip_root=True)` |
| 4 | finish W3 本地 CI 模拟 JC 拦截 | 仓库 main 上既有历史遗留文件（goaccess tarball 等），本地 full 模式全仓扫描命中；真实 CI 用 pr.diff 模式只查 PR 内文件 | 先提交 PR 文件使 diff 模式生效，重新跑 finish 通过 |

## 源码修改

无。stb_ds.h 与上游 v0.67 完全一致（sha256 校验通过），无补丁。
（test_package 内测试副本仅作 include 路径与编译模式适配，详见本地 reports/test-report.md）

## 依赖版本

- 无编译依赖（header-only 单头文件库）

## 验证结果

```bash
conan-verify stb_ds 0.67  → G0-G4 + L2/L4/L5 全部通过
finish stb_ds 0.67         → W3 本地 CI 模拟 exit_code=0（最终状态 built，CI 未 upload）
```

## 注意事项

- 上游 `Makefile all` 目标不编译 test_ds.c（上游 CI 仅跑 OSS-Fuzz），因此 clang 下此问题从未在上游暴露；已比对上游 master 的 STBDS_ADDRESSOF 宏与 v0.67 一致，属上游固有问题而非适配引入
- test_package 需同时编译 C 消费者测试与 C++ 上游测试，CMakeLists.txt 声明 `project(... C CXX)`
- conan-verify 的镜像注入会在本地把 conandata.yml 的 url 临时改为本地 file:// 路径并留 .ghfast-bak 备份，提交前必须恢复官方 URL 并清理备份残留（JC1 拦截）
---

**编译结束**: 2026-08-31 14:49
**最终状态**: built
