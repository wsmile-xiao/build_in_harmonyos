# lsyncd 2.3.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-17
- 编译器: clang/clang++
- 状态: built（已修复 CI #6693 的 host luac 缺失及 man page 安装路径问题，编译验证通过）

## 编译步骤

1. 下载 lsyncd 2.3.1 源码 (GitHub release-2.3.1 tag)
2. 下载 Lua 5.3.6 源码 (lua.org 官方)
3. 用 host cc 构建 host lua 和 luac（分别用于运行 bin2carray.lua 和编译 Lua 字节码）
4. 用 target clang 交叉编译 liblua.a (用于链接到 lsyncd 二进制)
5. 应用 0001-CMakeLists.txt.patch 修复 include 目录顺序
6. cmake configure: 传递 LUA_INCLUDE_DIR / LUA_LIBRARIES / LUA_EXECUTABLE / LUA_COMPILER
7. cmake build: 编译 lsyncd 二进制

关键 cmake 参数:
```
-DWITH_INOTIFY=True
-DWITH_FSEVENTS=False
-DLUA_INCLUDE_DIR=<lua-src>
-DLUA_LIBRARIES=<lua-src>/liblua.a
-DLUA_EXECUTABLE=<lua-dir>/host-lua
-DLUA_COMPILER=<lua-dir>/host-luac
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmd-pkgs 下载 Lua 5.3.6/5.4.8/5.4.7 全部返回 HTTP 404 | cmd-pkgs 仓库中没有 OHOS aarch64 预编译 Lua 包 | 改为从 lua.org 官方下载 Lua 5.3.6 源码，在 build() 中自行编译 |
| 2 | 交叉编译环境下 CMake find_package(Lua) 找不到 Lua | OHOS SDK 中没有 Lua 开发文件 | 通过 CMakeToolchain 显式传递 LUA_INCLUDE_DIR、LUA_LIBRARIES、LUA_EXECUTABLE |
| 3 | bin2carray.lua 需要 lua 解释器运行，但 target lua 无法在 CI host 上执行 | 交叉编译产生的 lua 解释器是 aarch64 架构，无法在 x86_64 CI worker 上运行 | 分两步构建 Lua: 先用 host cc 构建 host lua 解释器，再用 target cc 构建 target liblua.a |
| 4 | Lua 头文件目录中的 config.h 与 lsyncd build 目录的 config.h 冲突 | Lua 源码中有 config.h 文件，与 lsyncd 生成的 config.h 同名 | 应用 0001-CMakeLists.txt.patch，将 configure_file 和 include_directories(build_dir) 移到 Lua include 之前 |
| 5 | CI worker Python 可能缺少 ssl 模块导致 HTTPS 下载失败 | CI worker 环境精简 | 使用 curl 替代 Python urllib 进行 Lua 源码下载 |
| 6 | host lua 编译报错 `fatal error: 'readline/readline.h' file not found` | 使用 `-DLUA_USE_LINUX` 启用了 readline 支持，但 CI worker 未安装 readline 开发头文件 | 移除 `-DLUA_USE_LINUX`，host lua 仅用于运行 bin2carray.lua 脚本，不需要交互式 readline 功能 |
| 7 | `CMake.configure() got an unexpected keyword argument 'args'` | Conan 2 的 CMake.configure() 不支持 args 参数 | 在 generate() 中通过 CMakeToolchain 设置 Lua 缓存变量，build() 调用无参数的 cmake.configure() |
| 8 | `LUA_COMPILER-NOTFOUND` 导致 runner.out/defaults.out 生成失败 | 上游使用 `LUA_COMPILER` 调用 luac 编译 Lua 字节码，配方只构建并传递了 host lua | 同时构建 host luac，并通过 CMakeToolchain 设置 `LUA_COMPILER=<lua-dir>/host-luac` |
| 9 | `cmake.install()` 失败：`file cannot create directory: /man1` | CMakeLists.txt 使用 `${CMAKE_INSTALL_MANDIR}/man1` 作为 man page 安装路径，但未包含 `include(GNUInstallDirs)`，导致变量为空，路径变成绝对路径 `/man1` | 新增 0002-CMakeLists.txt-gnuinstalldirs.patch，添加 `include(GNUInstallDirs)` 使变量设为相对路径 `share/man` |

## 源码修改

- `patches/0001-CMakeLists.txt.patch`: 修复 include 目录顺序，将 configure_file(config.h) 和 include_directories(build_dir) 移到 find_package(Lua) 之后、include_directories(LUA_INCLUDE_DIR) 之前，确保 lsyncd 的 config.h 优先于 Lua 的 config.h
- `patches/0002-CMakeLists.txt-gnuinstalldirs.patch`: 添加 `include(GNUInstallDirs)`，使 `CMAKE_INSTALL_MANDIR` 被正确设置为相对路径 `share/man`，修复 man page 安装到绝对路径 `/man1` 导致的 `cmake.install()` 失败

## 依赖版本

- Lua 5.3.6 (从 https://www.lua.org/ftp/lua-5.3.6.tar.gz 源码构建)
  - SHA256: fc5fd69bb8736323f026672b1b7235da613d7177e72558893a0bdcd320466d60

## 验证结果

交叉编译环境 (x86_64 CI worker → aarch64 OHOS)，lsyncd 无 ctest 测试套件。
test_package 通过 VirtualRunEnv + bash wrapper 运行 `lsyncd --version` 验证二进制可用性。

## 注意事项

- Lua 是构建时依赖，不是运行时依赖。lsyncd 的 Lua 脚本在编译时通过 bin2carray.lua 内嵌为 C 数组，运行时不需要 lua 解释器
- host lua 和 luac 仅用于构建期间生成内嵌代码，不打包到最终产物中
- cmd-pkgs 中无 OHOS aarch64 预编译 Lua 包，必须从源码构建

---

**编译结束**: 2026-07-17
**当前状态**: built（已修复 host luac 缺失及 man page 安装路径问题，编译验证通过）
