# lua-resty-jwt

## 简介
lua-resty-jwt 是为 OpenResty 提供 JWT（JSON Web Token）支持的 Lua 库。

## OHOS 适配
- 纯 Lua 实现，无需编译 C 代码
- 直接复制 Lua 模块文件到正确的路径即可使用
- 运行时需要 OpenResty 环境或 ngx.lua

## 依赖
- lua >= 5.1
- lua-resty-string（OpenResty 标准库）

## 功能验证
```lua
local jwt = require "resty.jwt"
local token = jwt:sign("secret", {header={alg="HS256"}, payload={sub="user"}})
```

## 参考
- GitHub: https://github.com/SkyLothar/lua-resty-jwt
