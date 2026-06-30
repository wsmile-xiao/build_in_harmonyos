# lua-stringy 0.7

## 软件简介

lua-stringy 提供高性能的字符串操作函数（split、strip、find 等），使用 C 实现以提升性能。

- **主页**: https://github.com/mdeneen/lua-stringy
- **版本**: 0.7
- **构建系统**: Makefile
- **编译状态**: ✅ 成功

## OpenHarmony 适配说明

### 特殊处理

1. 手动编译（Makefile 需要 Lua 环境配置）
2. 显式链接 Lua 库（`-llua`）
3. ELF 签名

### 编译命令

```bash
clang -c -O3 -Wall -Werror -fPIC -I~/usr/local/include stringy.c
clang -shared stringy.o -L~/usr/local/lib -llua -o stringy.so
```

## 依赖

- **必需**: lua/5.4.7

## 使用说明

```lua
local stringy = require("stringy")
print(stringy.strip("  test  "))  -- 输出: test
```

## 编译产物

- `lib/lua/5.4/stringy.so` (30KB)

## 编译日期

2026-06-10

## 质量门禁

- G1-G4 全部通过
- ELF 签名: ✅ 完成
- 功能验证: ✅ 通过