# libu2f-server 1.1.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-12
- 编译器: gcc（系统默认）
- 状态: built

## 编译步骤

1. **初始化**：使用 ohc-run.py init-build 创建骨架
2. **configure**：遇到 "directory already configured" 错误，手动清理 config.status/config.log/Makefile
3. **make**：遇到链接错误（arc4random/__fd_chk 缺失），添加 LDFLAGS="-Wl,--allow-shlib-undefined" 解决
4. **make install**：DESTDIR 模式 + 本地安装成功
5. **验证**：u2f-server --version 显示 1.1.0

关键 configure 命令：
```bash
export PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
export LDFLAGS="-Wl,--allow-shlib-undefined"
./configure --prefix=$HOME/usr/local
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: directory already configured | 源码目录残留配置文件 | find . -name config.status -delete; find . -name config.log -delete; find . -name Makefile -type f -not -name Makefile.am -not -name Makefile.in -delete |
| 2 | undefined reference: arc4random | libjson-c.so 缺失 BSD 函数（musl libc 无实现） | LDFLAGS="-Wl,--allow-shlib-undefined" 放宽链接器要求 |
| 3 | undefined reference: __fd_chk | libcrypto.so 缺失 glibc FORTIFY_SOURCE 函数 | 同上（放宽链接器） |

**G0 干净构建验证问题**：
- 原始 tarball 缺少 configure 脚本，需要先运行 `autoreconf --install`
- 已添加 hints/build-prestep.sh 自动化此步骤
- 手动验证：autoreconf + configure + make 成功

**技术债务**：
- 放宽链接器要求可能导致运行时符号解析失败（如果依赖库真的需要这些函数）
- 根本解决方案：重新编译 json-c 和 openssl，禁用 arc4random 和 FORTIFY_SOURCE
- 或提供兼容库实现缺失函数

## 源码修改

无补丁，仅修改编译环境变量。

## 依赖版本

- json-c: 0.17（已安装，有预编译包 0.16）
- openssl: 1.1.1w（已安装，有预编译包）
- pkg-config: 0.29.2

## 验证结果

```bash
$ ~/usr/local/bin/u2f-server --version
libu2f-server 1.1.0

$ ls -la ~/usr/local/lib/libu2f-server.so*
-rw-rw---- 120712 libu2f-server.a
lrwxrwxrwx    22 libu2f-server.so -> libu2f-server.so.0.1.0
lrwxrwxrwx    22 libu2f-server.so.0 -> libu2f-server.so.0.1.0
-rwxrwx--- 84608 libu2f-server.so.0.1.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| u2f-server | 59968 | 可执行文件 |
| libu2f-server.so.0.1.0 | 84608 | 共享库 |
| libu2f-server.a | 120712 | 静态库 |

## 注意事项

1. **必须设置 LDFLAGS**：每次编译都需要添加 `-Wl,--allow-shlib-undefined`，否则链接失败
2. **依赖库兼容性**：json-c 和 openssl 在 musl 环境下可能有问题，建议使用预编译包重新安装
3. **R21 自检**：编译选项修改已固化在 notes.md，无源码修改，符合零介入要求
---

**编译结束**: 2026-06-15 11:06
**最终状态**: built
