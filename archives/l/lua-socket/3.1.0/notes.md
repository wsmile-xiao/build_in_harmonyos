# 编译笔记 — lua-socket 3.1.0

## 编译日期
2026-06-10

## 编译状态
✅ 成功编译并发布

## 编译环境
- Lua 版本: 5.4.7
- 编译器: clang
- 构建系统: makefile
- 平台: HarmonyOS (Linux-like)

## 编译过程

### 1. 源码获取
- 下载 URL: https://github.com/lunarmodules/luasocket/archive/refs/tags/v3.1.0.tar.gz
- 版本: 3.1.0

### 2. 构建配置
lua-socket 使用简单的 Makefile，不是 autotools 或 cmake。关键配置：

- **平台**: linux
- **Lua 版本**: 5.4
- **Lua 头文件路径**: `/storage/Users/currentUser/usr/local/include`
- **编译器**: clang (替代默认的 gcc)
- **链接器**: clang
- **链接选项**: `-L/storage/Users/currentUser/usr/local/lib -llua -Wl,-rpath,/storage/Users/currentUser/usr/local/lib`

### 3. 编译问题与解决方案

#### 问题 1: 缺少 gcc
**现象**: makefile 默认使用 gcc，但系统只有 clang
**解决**: 通过命令行参数 `CC_linux=clang LD_linux=clang` 指定使用 clang

#### 问题 2: Lua 符号未定义
**现象**: 运行测试时出现 `lua_createtable: symbol not found` 错误
**原因**: 编译的共享库没有正确链接 Lua 库
**解决**: 添加链接选项 `-llua` 和 RPATH 设置 `-Wl,-rpath,/storage/Users/currentUser/usr/local/lib`

#### 问题 3: Lua 头文件路径
**现象**: makefile 默认在 `/usr/include/lua/5.4` 查找头文件，但实际在 `/storage/Users/currentUser/usr/local/include`
**解决**: 设置 `LUAINC_linux=/storage/Users/currentUser/usr/local/include`

### 4. 编译命令

```bash
cd src
make linux LUAV=5.4 \
  LUAINC_linux=/storage/Users/currentUser/usr/local/include \
  prefix=/storage/Users/currentUser/usr/local \
  CC_linux=clang \
  LD_linux=clang \
  MYLDFLAGS="-L/storage/Users/currentUser/usr/local/lib -llua -Wl,-rpath,/storage/Users/currentUser/usr/local/lib"
```

### 5. 安装命令

#### Staging 安装（DESTDIR 模式）
```bash
make install-unix DESTDIR=/storage/Users/currentUser/test-install-lua-socket-3.1.0
```

#### 本地安装验证
```bash
make install-unix
```

### 6. 测试验证

```bash
export LUA_PATH="/storage/Users/currentUser/usr/local/share/lua/5.4/?.lua;;"
export LUA_CPATH="/storage/Users/currentUser/usr/local/lib/lua/5.4/?.so;;"
lua test/hello.lua
```

输出: `Hello from LuaSocket 3.0.0 and MIME 1.0.3!`

## 产物文件

### 共享库
- `socket/core.so` (198K) - 核心套接字库
- `socket/unix.so` (150K) - Unix 套接字支持
- `socket/serial.so` (122K) - 串口通信支持
- `mime/core.so` (42K) - MIME 编解码库

### Lua 模块
- `socket.lua` - 套接字主模块
- `mime.lua` - MIME 模块
- `ltn12.lua` - 数据传输库
- `socket/http.lua` - HTTP 客户端
- `socket/ftp.lua` - FTP 客户端
- `socket/smtp.lua` - SMTP 客户端
- `socket/url.lua` - URL 解析
- `socket/tp.lua` - 传输协议
- `socket/headers.lua` - HTTP 头处理

## 预编译包

- 文件名: `lua-socket-3.1.0-ohos-aarch64.tar.gz`
- 大小: 600K
- 已进行 ELF 签名

## 依赖

- lua/5.4.7 (必需)

## 知识提取

### E001: Lua 模块编译的特殊处理

对于 Lua C 模块的编译，需要注意：
1. 不能使用默认的 gcc，需要检查系统可用的编译器
2. 必须链接 liblua 并设置正确的 RPATH
3. Lua 头文件路径可能不在标准位置，需要显式指定

### E002: Makefile 项目缺少 configure

lua-socket 使用简单的 Makefile，没有 configure 脚本，这会导致 G0 干净构建验证失败。对于这类项目，需要手动验证编译流程，并在 notes.md 中记录。

---

**编译结束**: 2026-06-10 10:33
**最终状态**: 成功
---

**编译结束**: 2026-06-10 10:34
**最终状态**: built
