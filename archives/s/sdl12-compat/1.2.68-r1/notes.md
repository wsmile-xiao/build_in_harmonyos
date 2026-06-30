# sdl12-compat 1.2.68-r1 编译笔记

## Phase 1: 准备

- [x] 初始化编译环境
- [x] 查找源码 URL（GitHub libsdl-org/sdl12-compat release-1.2.68）
- [x] 下载源码（通过 GitHub API tarball）
- [x] 解压源码

## Phase 2: 配置与编译

- [x] 安装 SDL2 依赖（cmd-pkgs 预编译包 SDL2/2.30.0）
- [x] CMake configure: `-DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local -DCMAKE_BUILD_TYPE=Release`
- [x] CMake 成功找到 SDL2 (found version "2.30.0")
- [x] make -j1 编译成功，100% 完成
- [x] make install DESTDIR=$TEST_PREFIX 成功
- [x] 安装产物: bin=1(sdl-config) lib=5(libSDL-1.2.so, libSDLmain.a, libSDL.so, pkgconfig)

## Phase 2.5: Staging 验证

- [x] Staging verify 已通过

## Phase 3: 打包与收尾

- [x] Package 打包成功: sdl12-compat-1.2.68-r1-ohos-aarch64.tar.gz (1483KB)
- [x] Debug symbols 包: sdl12-compat-1.2.68-r1-ohos-aarch64-debug.tar.gz
- [x] G0 干净构建验证: 手动通过（cmake clean build）
- [x] finish 完成，status=published

## 对话记录

### 2026-06-04 编译过程

1. init-build: 使用 GitHub tarball URL 下载源码（Savannah SSL证书失败，改用 file:// 协议）
2. 依赖: SDL2/2.30.0 通过 cmd-pkgs 预编译包安装
3. configure: cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local -DCMAKE_BUILD_TYPE=Release ..（耗时3.9s）
4. make: 编译100%成功（耗时约15s）
5. install: DESTDIR模式安装成功
6. package: 打包1483KB，ELF签名完成
7. verify: 质量门禁G1-G4有警告，G0手动验证通过

## 遇到的问题与解决方案

| 问题 | 解决方案 |
|------|---------|
| Savannah SSL证书验证失败 | 改用 GitHub API tarball + file:// 协议 |
| SDL2 pkg-config 路径未设置 | 设置 PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig |
| G0 clean-verify 脚本不支持 cmake | 手动 cmake clean build 验证通过 |

## 知识提取

- sdl12-compat 是 SDL-1.2 兼容层，用 SDL-2.0 API 实现
- SDL2 依赖通过 cmd-pkgs 预编译包安装（2.30.0 版本）
- CMake 构建系统，需要 PKG_CONFIG_PATH 设置以找到 SDL2
- 生成的库文件名: libSDL-1.2.so（兼容层）而非 libSDL.so
---

**编译结束**: 2026-06-04 13:20
**最终状态**: published
