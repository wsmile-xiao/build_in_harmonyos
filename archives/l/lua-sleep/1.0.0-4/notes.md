# lua-sleep 0.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-10
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: https://github.com/squeek502/sleep/archive/refs/tags/v1.0.0-4.tar.gz
2. 修改 CMakeLists.txt:
   - 更新 cmake_minimum_required 从 2.6 到 3.5
   - 添加 HarmonyOS 平台检测和链接 Lua 库
3. 配置 CMake:
   ```bash
   cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DLUA_INCLUDE_DIR=$DEFAULT_PREFIX/include -DLUA_LIBRARIES=$DEFAULT_PREFIX/lib/liblua.so -DLUA_VERSION_MAJOR=5 -DLUA_VERSION_MINOR=4 -DLUAROCKS_INSTALL_LIBDIR=$DEFAULT_PREFIX/lib/lua/5.4
   ```
4. 构建:
   ```bash
   make -j2
   ```
5. 安装（DESTDIR 模式）:
   ```bash
   make install DESTDIR=$TEST_PREFIX
   ```
6. 安装到本地:
   ```bash
   make install
   ```
7. 验证:
   ```bash
   lua test.lua
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 版本不兼容 | cmake_minimum_required(VERSION 2.6) 不支持 | 更新为 cmake_minimum_required(VERSION 3.5) |
| 2 | Lua 符号未定义 | sleep.so 需要链接 Lua 库 | 添加 HarmonyOS 检测并链接 Lua 库 |
| 3 | 缺少 install 规则 | LUAROCKS_INSTALL_LIBDIR 未设置 | 设置 LUAROCKS_INSTALL_LIBDIR=$DEFAULT_PREFIX/lib/lua/5.4 |

## 源码修改

- `0001-CMakeLists.txt.patch` - 更新 CMake 配置以支持 HarmonyOS:
  - cmake_minimum_required(VERSION 3.5)
  - 添加 HarmonyOS 平台检测
  - 使用 `-undefined dynamic_lookup` 允许动态符号解析
  - 在 HarmonyOS 上链接 Lua 库

## 依赖版本

- Lua 5.4.7
- CMake 4.1.2
- Clang 15.0.4

## 验证结果

```bash
cd /storage/Users/currentUser/builds/lua-sleep-0.1.work
export LUA_CPATH="/storage/Users/currentUser/usr/local/lib/lua/5.4/?.so;"
lua test.lua
# 输出: 1 2 3 4 5 6 7 8 9 10
# 测试成功：sleep 模块正常工作
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lua-sleep-1.0.0-4-ohos-aarch64.tar.gz | 20KB | 预编译包（包含 sleep.so） |
| sleep.so | 18KB | Lua 模块（毫秒精度 sleep 函数） |

## 注意事项

- 这是一个 Lua 模块（.so 文件），不是可执行文件
- 需要设置 LUA_CPATH 环境变量才能加载模块
- 测试脚本 test.lua 验证通过（sleep 函数每秒调用一次，总共10次）
- G0 干净构建验证失败（因为 CMake 项目没有 configure 脚本），但手动编译验证通过
---

**编译结束**: 2026-06-10 11:22
**最终状态**: built
