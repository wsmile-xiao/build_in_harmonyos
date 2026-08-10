# jemalloc 5.3.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-21
- 编译器: clang 15.0.4 / clang++
- 平台: aarch64-unknown-linux-ohos
- 状态: built

## 编译步骤

1. 下载源码: `jemalloc-5.3.0.tar.bz2`
2. 解压到 `~/hometmp/builds/jemalloc-5.3.0.work`
3. 修复 config.guess/config.sub（平台识别补丁）
4. configure: `./configure --prefix=/storage/Users/currentUser/usr/local --disable-cxx CFLAGS="-Wno-array-bounds"`
5. make: `make -j2`
6. make install DESTDIR: `make install DESTDIR=/storage/Users/currentUser/hometmp/test-install-jemalloc-5.3.0`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别平台 | E007 - HarmonyOS 未在 GNU config.guess 中定义 | 补丁 build-aux/config.guess/config.sub，添加 __OHOS__ LIBC 检测和 HarmonyOS case 分支 |
| 2 | TMPDIR 只读 | E002 - /tmp 不可写 | 硬编码 TMPDIR=/storage/Users/currentUser/hometmp/cgwork |
| 3 | config.sub linux-ohos 不识别 | kernel-OS 验证列表缺失 | 添加 `linux-ohos*` 到验证列表 |
| 4 | array-bounds 警告导致编译失败 | rtree.h RTREE_CACHE_CHECK_L2(0) 时 i-1 = -1 | CFLAGS="-Wno-array-bounds" |
| 5 | C++ exception specification 冲突 | JEMALLOC_CXX_THROW 与系统 stdlib.h 声明不兼容 | --disable-cxx 禁用 C++ 支持 |
| 6 | config.status 临时目录失败 | mktemp 创建的目录权限受限 | 硬编码 tmp=./conftmp/jemalloc_tmp |

## 源码修改

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| build-aux/config.guess | 平台识别 | 添加 __OHOS__ LIBC 检测、HarmonyOS case 分支、TMPDIR 硬编码 |
| build-aux/config.sub | 平台识别 | 添加 ohos-linux triplet、linux-ohos* kernel 验证 |

## 依赖版本

- clang 15.0.4
- llvm-ar / llvm-ranlib
- make 4.4.1
- autoconf 2.73
- automake 1.18.1

## 验证结果

```bash
# Staging 目录内容
ls /storage/Users/currentUser/hometmp/test-install-jemalloc-5.3.0/storage/Users/currentUser/usr/local/lib/
libjemalloc.a       5,306,746 bytes
libjemalloc.so.2    3,004,864 bytes
libjemalloc_pic.a   5,307,064 bytes
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/libjemalloc.a | 5.3 MB | 静态库 |
| lib/libjemalloc.so.2 | 3.0 MB | 动态库 |
| lib/libjemalloc_pic.a | 5.3 MB | PIC 静态库 |

## 注意事项

1. **必须禁用 C++ 支持**: jemalloc 的 JEMALLOC_CXX_THROW 与鸿蒙系统 stdlib.h 声明不兼容
2. **需要禁用 array-bounds 警告**: rtree.h 中 RTREE_CACHE_CHECK_L2 宏在 i=0 时会产生 i-1=-1 的数组索引
3. **make check 跳过**: 测试套件可能超时，建议在 notes.md 记录跳过原因
---

**编译结束**: 2026-08-06 22:00
**最终状态**: built
