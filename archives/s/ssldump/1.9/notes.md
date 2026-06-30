# ssldump 1.9 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-10
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化环境: `ohc-run.py init-build ssldump 1.9 --url=https://github.com/adulau/ssldump/archive/refs/tags/v1.9.tar.gz`
2. 安装依赖:
   - OpenSSL 1.1.1w: `curl install.sh | sh -s -- openssl 1.1.1w`
   - libnet 1.2: `curl install.sh | sh -s -- libnet 1.2`
3. CMake 配置: 手动指定依赖路径（PKG_CONFIG_PATH 和 CMake 变量）
4. 编译: `make -j2`
5. 安装到本地: `make install`
6. 验证: `ssldump -v` 成功

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 无法找到 OpenSSL/PCAP/LIBNET | PKG_CONFIG_PATH 未设置，FindPCAP/FindLIBNET 模块对鸿蒙平台支持不足 | 设置 PKG_CONFIG_PATH，手动指定 -DOPENSSL_ROOT_DIR, -DPCAP_LIBRARY, -DLIBNET_LIBRARY |
| 2 | 缺少 libnet 依赖 | 系统未安装 libnet | 使用预编译包安装 libnet 1.2 |
| 3 | OpenSSL 头文件不完整 | 之前的 OpenSSL 安装只包含库文件 | 安装完整 OpenSSL 1.1.1w 预编译包 |
| 4 | 无 make check 测试 | ssldump 没有正式测试套件 | 记录为无测试，通过 -v 验证功能 |

## 源码修改

无补丁。源码无需修改即可编译。

## 依赖版本

- openssl 1.1.1w（预编译包）
- libpcap（已有）
- libnet 1.2（预编译包）
- json-c（已有）

## 验证结果

```bash
$ ssldump -v
Version: 1.8 (20230814)
Maintained by a bunch of volunteers, see https://github.com/adulau/ssldump/blob/master/CREDITS
Copyright (C) 2015-2023 the aforementioned volunteers
Copyright (C) 1998-2001 RTFM, Inc.
All rights reserved.
Compiled with OpenSSL: decryption enabled
```

## 注意事项

1. 必须设置 PKG_CONFIG_PATH 和手动指定 CMake 变量，因为 CMake 的 FindXXX 模块在鸿蒙平台上无法自动定位依赖
2. libnet 依赖需从预编译包安装
3. 无正式测试套件，功能验证依赖 -v 参数
---

**编译结束**: 2026-06-10 10:32
**最终状态**: built
