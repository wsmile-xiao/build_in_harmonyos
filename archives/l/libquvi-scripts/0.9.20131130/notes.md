# libquvi-scripts 0.9.20131130 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-07
- 编译器: clang/clang++
- 状态: built (conan-verify 通过, CI 模拟通过)

## 源码信息
- 官方源: https://repo.or.cz/libquvi-scripts.git
- 下载URL: https://repo.or.cz/libquvi-scripts.git/snapshot/refs/tags/v0.9.20131130.tar.gz
- SHA256: 1710a441c3625e235df5cbea25d21cf90396765aad729ddb6e70c82ed0fd31ee

## 编译步骤

1. 下载源码 (repo.or.cz git snapshot, tag v0.9.20131130)
2. 创建 VERSION 文件 (git snapshot 无 .git 目录, gen-ver.sh 需要此文件)
3. 运行 autoreconf -if 生成 configure 脚本
4. 修补 config.guess 添加 HarmonyOS 检测 (autoconf 2.73 版本不支持)
5. 修补 configure 脚本使用固定临时目录 (HMDFS 限制)
6. 修复 shebang 路径 (/bin/bash -> /data/service/hnp/bin/bash)
7. 运行 configure --without-manual (a2x 不可用)
8. make && make install DESTDIR

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | URL 缺失 | 不在 registry 中 | 从 repo.or.cz 找到 git tag snapshot URL |
| 2 | 无 configure 脚本 | git snapshot 无预生成文件 | 创建 VERSION 文件 + autoreconf -if |
| 3 | config.guess 无法识别平台 | autoconf 2.73 不含 HarmonyOS 检测 | 手动添加 HarmonyOS case 分支 |
| 4 | config.status 临时目录失败 | HMDFS 不允许在 mktemp 子目录中创建文件 | 使用固定目录 + chmod 777 |
| 5 | PKG_CHECK_MODULES 失败 | --without-tests 仍触发 libquvi 检查 | 不传递 --without-tests (默认即跳过) |
| 6 | man pages 构建失败 | a2x/asciidoc 不可用 | configure --without-manual |
| 7 | automake/aclocal 损坏 | cmd-pkgs 版本与 Perl 模块不匹配 | 使用 harmonybrew automake 1.18.1 |

## 源码修改

- config.aux/config.guess: 添加 HarmonyOS 检测分支
- config.aux/config.sub: 上游已支持 linux-ohos* (无需修改)
- configure: 修复临时目录创建逻辑
- VERSION: 创建版本文件

## 依赖版本

- autoconf: 2.73 (harmonybrew)
- automake: 1.18.1 (harmonybrew)
- libtool: 2.5.4 (harmonybrew)
- pkg-config: 0.29.2
- make: 4.4.1

## 验证结果

- conan-verify: G0-G4 全部通过
- 本地 CI 模拟 (W3): 通过
- test_package: 验证 Lua 脚本文件存在性和版本信息

## 注意事项

- libquvi-scripts 是纯 Lua 脚本包，无二进制文件
- 需要配合 libquvi 库使用
- 构建 类型为 unknown (无 shared/static 概念)
