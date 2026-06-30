# lua-socket 3.1.0

## 软件简介

LuaSocket 是 Lua 的网络支持库，提供 TCP/UDP 套接字、HTTP 客户端、FTP 客户端、SMTP 客户端等功能。

- **主页**: https://github.com/lunarmodules/luasocket
- **版本**: 3.1.0
- **构建系统**: Makefile
- **编译状态**: ✅ 成功

## OpenHarmony 适配说明

### 特殊处理

1. 使用 clang 编译器替代默认 gcc
2. 显式链接 Lua 库（`-llua`）
3. 设置正确的 RPATH

### 编译参数

```bash
make linux LUAV=5.4 \
  LUAINC_linux=/storage/Users/currentUser/usr/local/include \
  CC_linux=clang \
  LD_linux=clang \
  MYLDFLAGS="-L/storage/Users/currentUser/usr/local/lib -llua -Wl,-rpath,/storage/Users/currentUser/usr/local/lib"
```

## 依赖

- **必需**: lua/5.4.7

## 使用说明

```lua
local socket = require("socket")
-- 创建 TCP 套接字
local client = socket.connect("example.com", 80)
```

## 编译产物

### 共享库（已 ELF 签名）
- `lib/lua/5.4/socket/core.so` (198K) - 核心套接字库
- `lib/lua/5.4/socket/unix.so` (150K) - Unix 套接字
- `lib/lua/5.4/socket/serial.so` (122K) - 串口通信
- `lib/lua/5.4/mime/core.so` (42K) - MIME 编解码

### Lua 模块
- `share/lua/5.4/socket.lua` - 主模块
- `share/lua/5.4/socket/http.lua` - HTTP 客户端
- `share/lua/5.4/socket/ftp.lua` - FTP 客户端
- `share/lua/5.4/socket/smtp.lua` - SMTP 客户端
- `share/lua/5.4/mime.lua` - MIME 模块

## 编译日期

2026-06-10

## 质量门禁

- G1-G4 全部通过
- 功能验证: ✅ 通过