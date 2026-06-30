# lua-resty-string

## 简介

lua-resty-string 是 OpenResty 的字符串处理和加密库，提供常用哈希函数（MD5/SHA1/SHA256/SHA384/SHA512）和 AES 加密功能。

## OHOS 适配

- **类型**: 纯 Lua 库（使用 LuaJIT FFI）
- **编译**: 无需编译，直接安装 Lua 文件
- **依赖**: 需要 LuaJIT FFI + ngx_lua + OpenSSL
- **路径**: `$PREFIX/lib/lua/5.4/resty/`

### 已知问题

- 标准 Lua 5.x 无法运行（依赖 LuaJIT FFI）
- 需要 OpenResty 或 ngx_lua 环境

## 依赖

- LuaJIT (FFI支持)
- OpenSSL
- ngx_lua 或 OpenResty

## 功能验证

```bash
# Lua语法检查
luac -p $PREFIX/lib/lua/5.4/resty/*.lua
```

## 参考

- 官网: https://github.com/openresty/lua-resty-string
- 许可证: BSD-2-Clause