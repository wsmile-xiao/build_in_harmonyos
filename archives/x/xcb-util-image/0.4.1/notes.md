# xcb-util-image 0.4.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-09
- 编译器: clang/clang++
- 状态: published

## 编译步骤

使用 x.org 官方 release tarball（包含预生成 configure 和 m4 宏），通过 Conan 配方自动完成：
1. 下载 release tarball 并解压
2. 应用补丁修复 -Werror=return-type
3. configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu
4. make && make check
5. make install

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | xcb-util/0.4.0 缺失 | 制品仓无 xcb-util 包 | 适配 xcb-util/0.4.1 作为依赖并本地构建 |
| 2 | xcbproto_version 变量缺失 | Conan PkgConfigDeps 生成的 xcb.pc 缺少自定义变量 | 从 libxcb 包原始 xcb.pc 复制 xcbproto_version |
| 3 | xcb-shm.pc 不可见 | PkgConfigDeps 只生成 xcb.pc，扩展库的 .pc 在包目录中 | 复制 libxcb 包的扩展 .pc 文件到 generators 目录 |
| 4 | -Werror=return-type | xcb_host_byte_order() 在 assert(0) 后无 return | 补丁添加 unreachable return |
| 5 | .la 依赖路径失效 | libtool .la 文件中的 dependency_libs 引用构建时路径 | 修复 libdir 并将 .la 引用替换为 -l 标志 |

## 源码修改

- patches/0001-fix-xcb_bitops-return-type.patch: 修复 xcb_bitops.h 中 xcb_host_byte_order() 函数的 -Werror=return-type 错误

## 依赖版本

- libxcb/1.17.0
- xorgproto/2025.1
- xcb-util/0.4.1

## 验证结果

```bash
$ conan create archives/x/xcb-util-image/0.4.1/conanfile.py --name xcb-util-image --version 0.4.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# 编译成功，test_package 测试通过
xcb-util-image api smoke ok
```

## 注意事项

- xcb-util/0.4.1 需要先发布到制品仓，否则下游 CI 构建会失败
- libxcb 的扩展 .pc 文件（xcb-shm.pc 等）需要手动复制到 generators 目录
---

**编译结束**: 2026-08-09 01:37
**最终状态**: published
