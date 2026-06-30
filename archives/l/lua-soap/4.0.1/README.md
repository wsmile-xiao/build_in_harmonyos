# lua-soap 4.0.1

## 软件简介

lua-soap 是一个纯 Lua 实现的 SOAP（Simple Object Access Protocol）客户端和服务器库，支持 WSDL（Web Services Description Language）解析。

- **主页**: https://github.com/tomasguisasola/luasoap
- **版本**: 4.0.1
- **构建系统**: Makefile
- **编译状态**: ✅ 成功

## OpenHarmony 适配说明

### 特殊处理

lua-soap 是纯 Lua 库，无需编译步骤，仅需安装 Lua 文件到正确的路径。

### 主要修改

1. **Makefile 补丁**: 添加 DESTDIR 支持，移除不存在的 https.lua 引用
2. **Lua 版本**: 调整为 Lua 5.4（匹配系统版本）

### 补丁文件

- `0001-Makefile.patch`: DESTDIR 支持和文件列表调整

## 依赖

- **必需**: lua/5.4.7
- **运行时依赖**（需单独安装）:
  - luaexpat (lxp.lom 模块)
  - luasocket
  - http-digest

## 使用说明

安装后需设置 LUA_PATH 环境变量：

```bash
export LUA_PATH="/storage/Users/currentUser/usr/local/share/lua/5.4/?.lua;;"
```

示例代码：

```lua
local soap = require "soap"
-- 使用 SOAP 客户端功能
```

## 编译产物

- `share/lua/5.4/soap.lua` - 主模块
- `share/lua/5.4/soap/client.lua` - 客户端模块
- `share/lua/5.4/soap/server.lua` - 服务器模块
- `share/lua/5.4/soap/wsdl.lua` - WSDL 解析模块

## 编译日期

2026-06-10

## 质量门禁

- G1-G4 全部通过
- 功能验证: ✅ 通过