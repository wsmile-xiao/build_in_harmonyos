# highlight 4.18 编译笔记

## 编译日期
2026-05-28

## 编译状态
编译成功，生成 CLI 二进制文件

## 源码下载
- URL: http://www.andre-simon.de/zip/highlight-4.18.tar.bz2
- 备用: 从官网成功下载（初始尝试 SourceForge 和 GitHub 镜像均超时）

## 编译依赖
1. **Lua**: 使用标准 Lua 5.3（liblua.a），而非 LuaJIT
   - LuaJIT 是 Lua 5.1，不兼容 Diluculum 使用的 Lua 5.2+ API
   - 缺少的关键函数: lua_setglobal, lua_getglobal, lua_pcallk, lua_rotate, lua_rawlen

2. **Boost**: 只需要头文件（headers-only）
   - 主要使用: scoped_array, bind, xpressive
   - 系统已有完整的 Boost 头文件

## 编译过程

### 修改点

1. **修改 src/makefile**
   - 将 `LUA_PKG_NAME` 从 `lua5.3` 改为 `lua`
   - 创建 `/storage/Users/currentUser/usr/local/lib/pkgconfig/lua.pc`
   - 添加 `-D__OHOS__` 到 CFLAGS（解决 musl pthread_cancel 问题）
   - 添加 Boost 头文件路径: `-I/storage/Users/currentUser/usr/local/include`

2. **修改 Boost 头文件**
   - 文件: `/storage/Users/currentUser/usr/local/include/boost/core/detail/sp_thread_sleep.hpp`
   - 添加 `|| defined(__OHOS__)` 跳过 `pthread_setcancelstate`（musl 不支持）
   - 修改了两处条件判断

3. **编译器设置**
   - 使用完整路径: `CXX=/data/service/hnp/bin/clang++`
   - 标准库: 使用 libc++ (clang 默认)

### 编译命令
```bash
export CXX=/data/service/hnp/bin/clang++
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
cd /storage/Users/currentUser/builds/highlight-4.18.work/src
make lib-static
make cli
```

### 安装命令
```bash
cd /storage/Users/currentUser/builds/highlight-4.18.work
make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX
```

## 编译产物
- 二进制文件: `/storage/Users/currentUser/test-install-highlight-4.18/storage/Users/currentUser/usr/local/bin/highlight`
- 文件类型: ELF shared object, 64-bit LSB arm64, dynamic
- 文件大小: 1.8 MB
- 版本验证: `highlight version 4.18` ✅

## 测试结果
- 版本信息显示正常 ✅
- 语法高亮功能需要配置文件路径设置（--data-dir 参数）

## 编译问题总结

### 问题1: pthread_setcancelstate 未定义
- **错误**: Boost 使用了 musl/OHOS 不支持的 pthread_cancel 函数
- **解决**: 修改 Boost 头文件，添加 `|| defined(__OHOS__)` 条件判断
- **知识沉淀**: E051 - musl 不支持的 syscall

### 问题2: Lua API 不兼容
- **错误**: LuaJIT 缺少 lua_setglobal 等 Lua 5.2+ API
- **解决**: 使用标准 Lua 5.3（liblua.a）
- **知识沉淀**: Diluculum 需要 Lua 5.2+，不兼容 LuaJIT

### 问题3: 编译器路径硬编码
- **现象**: make 使用硬编码路径 `/home/runner/work/...`
- **解决**: 显式设置环境变量 `CXX=/data/service/hnp/bin/clang++`
- **原因**: 可能是系统 make 配置问题
---

**编译结束**: 2026-05-28 10:01
**最终状态**: built
---

**编译结束**: 2026-05-28 10:07
**最终状态**: built
