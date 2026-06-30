# libgit2 1.9.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化编译环境：ohc-run.py init-build libgit2 1.9.4 --url=https://github.com/libgit2/libgit2/archive/refs/tags/v1.9.4.tar.gz
2. cmake 配置：cmake -B build -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_TESTS=ON
3. 编译：cmake --build build -j2
4. 安装：cmake --install build --prefix $DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
5. 打包：ohc-run.py package libgit2 1.9.4
6. 验证：ohc-run.py verify-build libgit2 1.9.4

## 遇到的问题与解决方案

无需修改源码，使用默认配置即可编译成功。

## 源码修改

无

## 依赖版本

- openssl: 1.1.1w（预编译包）
- zlib: 1.3.1（预编译包）
- cmake: 4.1.2（构建工具）

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/bin/git2 --help
usage: git2 [--help] [-c <key=value>] [--config-env=<key=value>] [--no-pager]
             [--version] <command> [<args>...]

These are the git2 commands available:
   blame        Show the origin of each line of a file
   cat-file     Display an object in the repository
   clone        Clone a repository into a new directory
   config       View or set configuration values 
   hash-object  Hash a raw object and product its object ID
   help         Display help information
   index-pack   Create an index for a packfile
   init         Create a new git repository
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libgit2-1.9.4-ohos-aarch64.tar.gz | 8.6MB | 主包 |
| libgit2-1.9.4-ohos-aarch64-debug.tar.gz | 6.6MB | 调试包 |

## 注意事项

- libgit2 使用 cmake 构建系统，依赖 openssl 和 zlib
- 启用 BUILD_TESTS=ON 编译测试套件
- 编译产物包含 git2 命令行工具和 libgit2.so 共享库
---

**编译结束**: 2026-05-27 18:25
**最终状态**: built
