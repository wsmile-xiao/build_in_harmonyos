# lrexlib (lua-rex)

## 简介

lrexlib 是 Lua 的正则表达式库，支持多种正则引擎（POSIX、PCRE、Oniguruma）。

## OHOS 适配

- **类型**: Lua C 模块（.so）
- **编译**: 使用 autotools 构建系统
- **版本**: 2.9.1（仅编译 POSIX 版本）
- **路径**: `$PREFIX/lib/lua/5.4/rex_posix.so`

### 适配要点

- 仅编译 POSIX 正则版本（其他版本需额外依赖）
- 需要链接 Lua 库（解决符号未定义问题）
- 手动编译而非 LuaRocks 构建

## 依赖

- Lua 5.4.7
- POSIX regex 库

## 功能验证

```bash
# 加载模块测试
lua -e "local rex = require('rex_posix'); print(rex.match('hello', 'h.*o'))"
```

## 参考

- 官网: https://github.com/rrthomas/lrexlib
- 许可证: MIT