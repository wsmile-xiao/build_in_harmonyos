# minisign 0.12-r1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-04
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 GitHub jedisct1/minisign 下载 0.12 版本源码
2. 下载 Savannah 链接因 SSL 证书问题失败，改用 GitHub URL
3. libsodium 1.0.22 通过 cmd-pkgs 预编译包安装（R18）
4. CMake 配置需要显式指定 SODIUM_INCLUDE_DIR 和 SODIUM_LIBRARY，因为 libsodium 安装在非标准路径 ~/usr/local
5. libsodium.so 和 libsodium.so.26 soname symlink 缺失，需要手动创建
6. 编译命令：
   ```bash
   mkdir build && cd build
   cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
     -DSODIUM_INCLUDE_DIR=$HOME/usr/local/include \
     -DSODIUM_LIBRARY=$HOME/usr/local/lib/libsodium.so ..
   make -j2
   make install DESTDIR=$TEST_PREFIX
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | Python urllib 缺少 CA 证书 | export SSL_CERT_FILE=/storage/Users/currentUser/usr/local/ssl/cert.pem |
| 2 | SODIUM_LIBRARY NOTFOUND | libsodium 在非标准路径，CMake find_library 搜索路径不含 ~/usr/local/lib | 显式指定 -DSODIUM_INCLUDE_DIR 和 -DSODIUM_LIBRARY |
| 3 | make 找不到 libsodium.so | libsodium.so symlink 缺失 | rm -f && ln -s libsodium.so.26.4.0 libsodium.so (HMDFS 安全方式) |
| 4 | 运行时找不到 libsodium.so.26 | soname symlink 缺失 | ln -s libsodium.so.26.4.0 libsodium.so.26 |
| 5 | minisign 执行权限被拒 | 未 ELF 签名 | ohc-run.py sign-elf |

## 依赖版本

- libsodium 1.0.22 (cmd-pkgs 预编译包)

## 验证结果

```bash
$ $DEFAULT_PREFIX/bin/minisign -v
minisign 0.12
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| minisign | 22936 bytes | ELF binary, stripped, dynamically linked |

## 注意事项

- minisign 不支持 --version，使用 -v 选项查看版本
- libsodium 运行时需要 LD_LIBRARY_PATH 包含 ~/usr/local/lib 或设置 RPATH
---

**编译结束**: 2026-06-04 15:00
**最终状态**: published
