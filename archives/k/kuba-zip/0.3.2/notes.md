# kuba-zip 0.3.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4 (aarch64-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 源码: https://github.com/kuba--/zip 正式标签 v0.3.2 (commit 6f2116d7)
# 探索性编译
cmake -S . -B build-explore -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_SHARED_LIBS=ON
make -j2
# 上游测试
ctest --output-on-failure
# Conan 配方验证（干净构建）
conan create archives/k/kuba-zip/0.3.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 test_permissions 失败（33152 vs 33200） | E046: HMDFS/SELinux 忽略 chmod()，权限位断言失效（平台限制，非库缺陷） | 记录不阻塞；知识库 E046 命中 |
| 2 | test_package 编译找不到 zip.h | 上游把头文件安装到 `include/zip/zip.h` | test.c 改 `#include "zip/zip.h"` |
| 3 | test_package 编译参数错误 | `zip_entry_read` 签名是 `(void **buf, size_t *bufsize)` | 按上游 test_read.c 用法修正 |

## 源码修改

无补丁（patches/ 为空）。

## 依赖版本

无第三方依赖（仅上游自带 miniz.h，单头文件内嵌）。

## 验证结果

- 上游测试: 7/8 通过（test_permissions 为 E046 平台限制）
- conan-verify: G0-G4 + L2/L4/L5 全部 PASS
- test_package: 写入→读取 roundtrip PASS（R34 实质调用）

## 注意事项

- 头文件安装路径为 `include/zip/zip.h`，消费者需 `#include "zip/zip.h"`
- 库名 libzip.a，`package_info().libs = ["zip"]`
- CMake 项目 project(zip)，CMake 目标为 `zip`/`zip::zip`
---

**编译结束**: 2026-09-03 09:38
**最终状态**: built
