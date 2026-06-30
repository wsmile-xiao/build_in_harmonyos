# lua-stdlib-normalize 2.0.3 适配笔记

## 编译环境
- 构建系统: makefile (纯 Lua 库)
- 编译日期: 2026-06-10
- 编译器: 无 (纯 Lua 库，无需编译器)
- Lua 版本: 5.4.7
- 状态: published

## 编译步骤

此软件为纯 Lua 库，无需传统的 configure/make 流程：
1. 从 GitHub 下载源码: lua-stdlib/normalize v2.0.3
2. 解压源码包到工作目录
3. 识别为 Lua 库，无 configure 步骤
4. 手动安装 Lua 文件到目标目录

**安装步骤**:
```bash
# 创建目标目录
mkdir -p ~/usr/local/share/lua/5.4/std/normalize

# 复制 Lua 模块文件
cp lib/std/normalize/*.lua ~/usr/local/share/lua/5.4/std/normalize/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 缺少依赖 std._debug | lua-stdlib-normalize 依赖 std._debug 模块 | 从 lua-stdlib/_debug v1.0.1 下载并手动安装 |
| 2 | Lua 无法找到模块 | Lua 搜索路径为 /usr/local/share/lua/5.4/，而非 ~/usr/local/ | 设置 LUA_PATH 环境变量包含 ~/usr/local/share/lua/5.4/ |
| 3 | 无标准 install 目标 | Makefile 仅用于文档生成和测试，无 install 目标 | 手动复制文件到正确位置 |
| 4 | ohc-run.py build 失败 | 脚本期望标准 autotools/make install 流程 | 使用手动安装方式 |

## 源码修改

无补丁，无源码修改。

## 依赖版本

- lua/5.4.7
- std._debug/1.0.1

## 验证结果

```bash
# 设置 Lua 模块搜索路径
export LUA_PATH="/storage/Users/currentUser/usr/local/share/lua/5.4/?.lua;/storage/Users/currentUser/usr/local/share/lua/5.4/?/init.lua;;"

# 验证模块加载
lua -e "local n = require 'std.normalize'; print('版本:', n.version)"

# 输出:
# lua-stdlib-normalize 已安装成功
# 版本: Normalized Lua Functions / 2.0.3
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/std/normalize/*.lua | 5 files, ~52KB | Lua 模块文件（init.lua, _base.lua, _strict.lua, _typecheck.lua, version.lua） |

## 注意事项

1. 此库为纯 Lua 库，无需 C 编译器
2. 必须先安装 std._debug 依赖
3. 需要设置 LUA_PATH 环境变量以正确加载模块
4. Makefile 中的 check 目标需要 specl 工具（可选）
5. 对于预编译包制作，需要同时打包 std._debug 和 std.normalize 模块
---

**编译结束**: 2026-06-10 11:10
**最终状态**: built
