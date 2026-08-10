# 编译笔记 — lua-socket 3.1.0

## 编译日期
2026-08-07

## 编译状态
✅ 成功编译验证 (built)

## 编译环境
- Lua 版本: 5.4.8 (Conan 依赖)
- 编译器: clang 15.0.4
- 构建系统: makefile
- 平台: HarmonyOS (aarch64)

## 编译过程

### 1. 源码获取
- 下载 URL: https://github.com/lunarmodules/luasocket/archive/refs/tags/v3.1.0.tar.gz
- 版本: 3.1.0
- sha256: bf033aeb9e62bcaa8d007df68c119c966418e8c9ef7e4f2d7e96bddeca9cca6e

### 2. 构建配置
lua-socket 使用简单的 Makefile，不是 autotools 或 cmake。关键配置：

- **平台**: linux
- **Lua 版本**: 5.4
- **Lua 头文件路径**: 从 Conan 依赖 lua/5.4.8 自动获取
- **编译器**: 从 Conan conf 获取 (clang)
- **链接器**: 同编译器
- **链接选项**: `-L<lua_lib_dir> -llua -lm -ldl`

### 3. 编译问题与解决方案

#### 问题 1: 缺少 gcc
**现象**: makefile 默认使用 gcc，但系统只有 clang
**解决**: 通过命令行参数 `CC_linux=clang LD_linux=clang` 指定使用 clang

#### 问题 2: Lua 符号未定义
**现象**: 编译的共享库没有正确链接 Lua 库
**解决**: 添加链接选项 `-llua -lm -ldl`

#### 问题 3: Lua 头文件路径
**现象**: makefile 默认在 `/usr/include/lua/5.4` 查找头文件
**解决**: 设置 `LUAINC_linux` 指向 Conan 依赖的 include 目录

#### 问题 4: Conan conf 子键访问
**现象**: `self.conf.get("tools.build:compiler_executables:c")` 抛出异常
**解决**: 先获取整个 dict: `self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)`, 再取 `.get("c", "clang")`

#### 问题 5: CMakeDeps 默认 include 目录
**现象**: CMakeDeps 自动添加 `include/` 到 INTERFACE_INCLUDE_DIRECTORIES，但 lua-socket 没有头文件
**解决**: 在 package_info() 中设置 `self.cpp_info.includedirs = []`

### 4. 编译命令

```bash
make linux LUAV=5.4 \
  LUAINC_linux=<lua_include_dir> \
  CC_linux=<cc> LD_linux=<cc> \
  MYLDFLAGS="-L<lua_lib_dir> -llua -lm -ldl"
```

### 5. 安装命令

```bash
make install-unix DESTDIR=<package_folder> prefix= LUAV=5.4
```

### 6. 测试验证

```bash
lua test/hello.lua
```

输出: `Hello from LuaSocket 3.0.0 and MIME 1.0.3!`

## 产物文件

### 共享库 (Lua C 扩展模块)
- `lib/lua/5.4/socket/core.so` - 核心套接字库
- `lib/lua/5.4/socket/unix.so` - Unix 套接字支持
- `lib/lua/5.4/socket/serial.so` - 串口通信支持
- `lib/lua/5.4/mime/core.so` - MIME 编解码库

### Lua 模块
- `share/lua/5.4/socket.lua` - 套接字主模块
- `share/lua/5.4/mime.lua` - MIME 模块
- `share/lua/5.4/ltn12.lua` - 数据传输库
- `share/lua/5.4/socket/http.lua` - HTTP 客户端
- `share/lua/5.4/socket/ftp.lua` - FTP 客户端
- `share/lua/5.4/socket/smtp.lua` - SMTP 客户端
- `share/lua/5.4/socket/url.lua` - URL 解析
- `share/lua/5.4/socket/tp.lua` - 传输协议
- `share/lua/5.4/socket/headers.lua` - HTTP 头处理

## 依赖

- lua/5.4.8 (必需，Conan 制品仓已发布)

## Conan 适配说明

本次适配在原有手动编译基础上添加了 Conan 配方 (conanfile.py)：
- 从 Conan 依赖自动获取 Lua 头文件和库路径
- 编译器从 Conan conf 获取，不依赖 shell 环境变量 (R33)
- test_package 嵌入 Lua 解释器，通过 require() 加载 socket/mime 模块
- conan create 验证通过，test_package 测试通过

---

**编译结束**: 2026-08-07
**最终状态**: built
**Conan 适配完成**: conan-verify 全部通过 (G1-G4, L2/L4/L5)
