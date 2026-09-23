# libbz2 1.0.8 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-09-08
- 编译器: clang
- 状态: built
- 上游版本: 1.0.8
- 适配版本: 1.0.8（libbz2 包名，上游 bzip2 v1.0.8）

## 与 1.0.8.1 的差异
- 填写 url 字段（P2 CS5 修复）
- 添加 package_type = "library"（P3 CS2 修复）
- 移除空 requirements() 方法（P3 CS3 修复）
- 改进 patch_description 格式（P3 CS12 修复）
- test_package 使用 package_folder 替代 aggregated_components()

## 编译步骤
```bash
patch -p1 < patches/0001-Makefile.patch
make CC=clang AR=llvm-ar RANLIB=llvm-ranlib SHELL=/data/service/hnp/bin/bash -j1
make install PREFIX=$HOME/usr/local
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 静态库缺少 -fPIC | Makefile CFLAGS 无 -fPIC | 补丁自动检测 OHOS 添加 -fPIC |
| 2 | ln -sf 创建错误文件 | 鸿蒙 ln -sf bug | 配方禁用 shared=True |
| 3 | SHELL=/bin/sh 不存在 | OHOS 系统无 /bin/sh | 通过 CONFIG_SHELL 环境变量传入 bash 路径 |
| 4 | conan create 报 ConanException | tools.build:compiler_executables 是 dict，不能用 :c 后缀 | 改用 dict.get("c") 方式获取编译器 |

## 验证结果
```bash
bzip2 --version  # ✅ Version 1.0.8, 13-Jul-2019
# Upstream embedded tests: 12/12 PASS (6 compress/uncompress + 6 cmp)
# conan create + test_package: PASS
```
---

**编译结束**: 2026-09-08 10:05
**最终状态**: built
