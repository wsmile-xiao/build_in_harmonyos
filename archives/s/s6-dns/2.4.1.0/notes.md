# s6-dns 2.4.1.0 适配笔记

## 编译环境
- 构建系统: custom (skarnet configure + make)
- 编译日期: 2026-08-22
- 编译器: clang/clang++
- 状态: built

## 编译步骤

s6-dns 使用 skarnet 自有的 configure + make 构建系统（非标准 autotools/cmake）。

1. 下载并构建 skalibs 2.15.1.0（skalibs 未在 conan 制品仓发布，需从源码构建）
2. 构建 s6-dns 2.4.1.0（链接到本地构建的 skalibs）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | skarnet.org SSL 不可达 | 设备网络环境限制 | 使用 GitHub 官方镜像 (skarnet/s6-dns) 作为源码 URL |
| 2 | skalibs 未在 conan 制品仓发布 | 上游包未适配 | 在 conanfile.py build() 中从源码构建 skalibs |
| 3 | s6-dns 使用非标准构建系统 | skarnet 自有 configure | 不使用 Conan AutotoolsToolchain，手动调用 configure + make |

## 依赖版本

- skalibs 2.15.1.0 (从源码构建，GitHub: skarnet/skalibs v2.15.1.0)

## 验证结果

W3 本地 CI 模拟通过，conan create + L1 test_package 均通过。

## 交付物

- 18 个 CLI 工具 (s6-dnsq, s6-dnsqr, s6-dnsip, s6-dnsmx 等)
- 2 个静态库 (libs6dns.a, libskadns.a)
- 15 个头文件 (include/s6-dns/)

<!-- COMPLETED: s6-dns 2.4.1.0 adaptation complete -->
---

**编译结束**: 2026-08-23 00:37
**最终状态**: published
