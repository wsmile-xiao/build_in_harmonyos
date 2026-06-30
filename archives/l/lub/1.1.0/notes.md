# lub 1.1.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-15
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 搜索 lub 源码：
   - 使用 LuaRocks 搜索：https://luarocks.org/modules/gaspard/lub/1.1.0-1
   - 下载 rockspec 和 src.rock 文件
   - 从 src.rock 中提取源码（src.rock 是 zip 格式）

2. 打包源码：
   - 解压 src.rock 到 lub 目录
   - 打包成 lub-1.1.0.tar.gz（不包含父目录）

3. 初始化编译环境：
   - 使用 ohc-run.py init-build lub 1.1.0 --url=file:///path/to/lub-1.1.0.tar.gz

4. 配置：
   - 修改 CMakeLists.txt：cmake_minimum_required(VERSION 2.8) → (VERSION 3.5)
   - cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DLUA_INSTALL_DIR=$DEFAULT_PREFIX/share/lua/5.4

5. 编译和安装：
   - make install DESTDIR=$TEST_PREFIX（staging）
   - make install（安装到 DEFAULT_PREFIX）

6. 质量门禁：
   - verify-build 通过（G1-G4）
   - package 生成预编译包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lub.io 网站无法下载 | SSL 证书验证失败 + lub.io 域名已停用 | 从 LuaRocks 下载 src.rock 文件并解压 |
| 2 | CMake 版本不兼容 | CMakeLists.txt 要求 VERSION 2.8，当前 CMake 4.1.2 已移除支持 | 修改为 cmake_minimum_required(VERSION 3.5) |
| 3 | G4 档案完整性失败 | manifest 缺少 build_system 字段 | 在 manifest.yaml 顶层添加 build_system: cmake |

## 源码修改

无补丁文件，但在编译过程中修改了 CMakeLists.txt：
- 第 9 行：cmake_minimum_required(VERSION 2.8) → cmake_minimum_required(VERSION 3.5)

## 依赖版本

lub 依赖：
- lua >= 5.1, < 5.4（运行时依赖，已安装）
- luafilesystem >= 1.4.0（运行时依赖，用于 lub.Dir 功能，需要单独编译）

本次编译使用的工具版本：
- cmake: 4.1.2
- clang: 15.0.4

## 验证结果

lub 是纯 Lua 包，无二进制文件，无需 ELF 签名。
质量门禁 G1-G4 全部通过。

依赖 luafilesystem 未安装，lub 的完整功能需要先安装 luafilesystem。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lub-1.1.0-ohos-aarch64.tar.gz | 46KB | 预编译包（纯 Lua 文件） |

## 注意事项

1. lub 依赖 luafilesystem (lfs)，用于 lub.Dir 功能。如需完整功能，需先编译 luafilesystem。
2. 纯 Lua 包，无需 ELF 签名，可直接使用。
3. 源码来源：LuaRocks src.rock 文件，非标准 tarball。
---

**编译结束**: 2026-06-15 15:05
**最终状态**: built
