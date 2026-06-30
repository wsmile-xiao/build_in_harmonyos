# lua-resty-session

## 简介

lua-resty-session 是一个安全、灵活的会话管理库，用于 OpenResty。它提供了完整的会话生命周期管理，包括创建、存储、检索、修改和销毁会话。

## 主要特性

- 支持多种存储后端（cookie、memcached、redis 等）
- 支持多种加密算法（AES、HMAC）
- 支持多种编码格式（base64、hex、JSON）
- 支持会话压缩（zlib）
- 支持自定义会话标识符
- 完整的会话生命周期管理

## 安装方式

通过 cmd-pkgs 公共安装脚本：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- lua-resty-session 3.10
```

安装路径：`/usr/local/share/lua/5.4/resty/`

## 使用示例

```nginx
location /start {
    content_by_lua '
        local session = require "resty.session".start()
        session.data.name = "OpenResty Fan"
        session:save()
        ngx.say("Session started")
    ';
}
```

## 已编译版本

- **3.10** (2026-06-10): 纯 Lua 库，添加 Makefile install 目标支持 DESTDIR 模式

## 依赖关系

- 无编译依赖
- 运行依赖：Lua 5.4、OpenResty（可选）

## 更多信息

- 官方仓库：https://github.com/bungle/lua-resty-session
- 文档：README.md（源码仓库）
- LuaRocks：https://luarocks.org/modules/bungle/lua-resty-session