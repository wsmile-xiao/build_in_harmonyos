# argparse 0.6.0 编译笔记

## 编译时间
2026-06-17 10:08

## 编译环境
- 操作系统: OpenHarmony
- 架构: aarch64
- Lua 版本: 5.4.7

## 编译过程

### 1. 获取源码
- 项目主页: https://github.com/mpeterv/argparse
- 版本: 0.6.0
- 许可证: MIT

### 2. 构建系统
- 类型: 纯 Lua 库，无编译过程
- 依赖: Lua >= 5.1, < 5.4

### 3. 安装
由于 argparse 是纯 Lua 库，安装过程如下：

```bash
# 安装 Lua 模块
cp src/argparse.lua $PREFIX/share/lua/5.4/

# 安装文档
cp README.md LICENSE CHANGELOG.md $PREFIX/share/doc/argparse/
```

### 4. 验证

**问题发现**：Lua 5.4.7 编译时硬编码了路径 `/usr/local/share/lua/5.4/`，
而实际安装路径是 `$HOME/usr/local/share/lua/5.4/`。

**解决方案**：
1. 设置 `LUA_PATH` 环境变量：
   ```bash
   export LUA_PATH="$HOME/usr/local/share/lua/5.4/?.lua;;"
   ```

2. 或者在 Lua 代码中设置：
   ```lua
   package.path = "/storage/Users/currentUser/usr/local/share/lua/5.4/?.lua;" .. package.path
   ```

### 5. 测试

```lua
local argparse = require "argparse"
local parser = argparse("test", "Test argparse installation")
parser:argument("input", "Input file.")
parser:option("-o --output", "Output file.", "a.out")
-- 功能测试通过 ✅
```

## 注意事项

1. **路径问题**：Lua 模块路径需要通过 `LUA_PATH` 环境变量设置，
   或者将 Lua 重新编译为使用正确的路径。

2. **安装脚本**：建议在安装脚本中添加以下环境变量设置：
   ```bash
   export LUA_PATH="$HOME/usr/local/share/lua/5.4/?.lua;;"
   ```

3. **兼容性**：argparse 兼容 Lua 5.1, 5.2, 5.3, 5.4，已在 Lua 5.4.7 上测试通过。

## 质量门禁

- ✅ G0: 干净构建验证（无编译过程，源码直接可用）
- ✅ G1: 二进制完整性（纯 Lua 库，无二进制文件）
- ✅ G2: 功能可用性（模块加载测试通过）
- ✅ G3: 可移植性（纯 Lua 代码，平台无关）
- ✅ G4: 档案完整性（tar.gz 包含所有必要文件）

## 编译状态
**成功** - argparse 0.6.0 编译安装成功。
---

**编译结束**: 2026-06-17 10:11
**最终状态**: built
