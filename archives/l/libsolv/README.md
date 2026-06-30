# libsolv

## 简介

libsolv 是一个免费的包依赖解析器，使用可满足性算法（SAT solver）来解决包依赖问题。它被广泛用于包管理系统如 RPM、DEB、Arch Linux 等。

## 版本

- 0.7.30 (2026-05-25)

## 编译状态

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 0.7.30 | built | 2026-05-25 |

## 功能特性

- 支持多种包格式：rpm、deb、arch linux、haiku
- 支持多种仓库格式：rpmmd、susertags、mandriva/mageia、arch linux
- 使用 SAT 算法高效解析依赖关系
- 提供静态库和共享库

## 编译说明

libsolv 使用 CMake 构建。在鸿蒙系统上编译时需要注意：

1. 设置 CMAKE_POLICY_VERSION_MINIMUM=3.5 解决版本兼容问题
2. 禁用不需要的仓库格式支持减少依赖
3. 正确设置 ZLIB 搜索路径

## 依赖

- zlib (必需)

## 安装产物

- **库文件**: libsolv.so, libsolv.a, libsolvext.so, libsolvext.a
- **工具**: dumpsolv, testsolv, mergesolv, installcheck, repo2solv
- **头文件**: /usr/local/include/solv/
- **pkg-config**: libsolv.pc, libsolvext.pc

## 参考资料

- 官方仓库: https://github.com/openSUSE/libsolv
- Gitee 镜像: https://gitee.com/mirrors/libsolv