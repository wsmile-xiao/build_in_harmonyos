# lua-stdlib 41.2.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-10
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码：lua-stdlib 41.2.1 from GitHub
2. 修改 configure.ac：将 `AX_PROG_LUA([5.1], [5.4])` 改为 `AX_PROG_LUA([5.1], [5.5])` 以支持 Lua 5.4.7
3. 运行 autoreconf 重新生成 configure
4. 修复 HMDFS SELinux 限制：将 configure 中 `umask 077` 改为 `umask 022`
5. 运行 configure：`./configure --prefix=/storage/Users/currentUser/usr/local`
6. 运行 make：`make -j1`（无实际编译任务，纯 Lua 库）
7. 运行 make install：安装到 staging 目录和 DEFAULT_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报错：cannot find suitable Lua interpreter | Lua 版本检测范围是 5.1-5.3，不包含 Lua 5.4.7 | 修改 configure.ac：`AX_PROG_LUA([5.1], [5.5])`，重新运行 autoreconf |
| 2 | config.status 报错：Permission denied creating temp files | HMDFS SELinux 限制，umask 077 不允许创建临时文件 | 执行 `sed -i 's/umask 077/umask 022/g' configure` |
| 3 | make check 跳过测试 | 缺少 specl 测试框架 | 记录跳过原因，不影响功能 |

## 源码修改

### 补丁列表（7 个）
- `0001-INSTALL.patch` - autoreconf 自动生成的 INSTALL 文件更新
- `0002-Makefile.in.patch` - autoreconf 自动生成的 Makefile.in 更新
- `0003-aclocal.m4.patch` - autoreconf 自动生成的 aclocal.m4 更新
- `0004-build-aux-install-sh.patch` - autoreconf 自动生成的 install-sh 更新
- `0005-build-aux-missing.patch` - autoreconf 自动生成的 missing 更新
- `0006-configure.patch` - autoreconf 重新生成的 configure（含 umask 修复）
- `0007-configure.ac.patch` - 手动修改：支持 Lua 5.4

### 关键修改点
1. **configure.ac（第 32 行）**：
   ```diff
   -AX_PROG_LUA([5.1], [5.4])
   +AX_PROG_LUA([5.1], [5.5])
   ```
   原因：Lua 5.4 的版本号是 504，原代码检查 `ver < maxver`（507 < 504）不成立

2. **configure（第 4177, 4182 行）**：
   ```diff
   -(umask 077 && mktemp -d "./confXXXXXX")
   +(umask 022 && mktemp -d "./confXXXXXX")
   ```
   原因：HMDFS SELinux 限制，umask 077 导致临时目录创建失败

## 依赖版本

- Lua 5.4.7（系统已安装）
- autoconf 2.72
- automake 1.17

## 验证结果

```bash
# 设置 LUA_PATH 环境变量
export LUA_PATH="/storage/Users/currentUser/usr/local/share/lua/5.4/?.lua;/storage/Users/currentUser/usr/local/share/lua/5.4/?/init.lua;;"

# 加载 stdlib 模块
lua -e 'local std = require "std"; print("stdlib loaded successfully")'
# 输出：stdlib loaded successfully
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lua-stdlib-41.2.1-ohos-aarch64.tar.gz | 567KB | 预编译包（纯 Lua 文件） |

安装内容：
- `/usr/local/share/lua/5.4/std.lua` - 主模块
- `/usr/local/share/lua/5.4/std/*.lua` - 子模块（17 个文件）
- `/usr/local/share/doc/stdlib/` - 文档文件

## 注意事项

1. **LUA_PATH 设置**：
   - Lua 默认 package.path 使用硬编码 `/usr/local`
   - 需要设置环境变量：`export LUA_PATH="$HOME/usr/local/share/lua/5.4/?.lua;$HOME/usr/local/share/lua/5.4/?/init.lua;;"`

2. **无二进制文件**：
   - lua-stdlib 是纯 Lua 库，没有二进制可执行文件
   - 所有文件都是 `.lua` 文本文件，不需要 ELF 签名

3. **测试跳过**：
   - 需要 specl 测试框架（OHOS 上未安装）
   - 功能验证通过手动加载测试

---
**编译结束**: 2026-06-10 10:33
**最终状态**: built
---

**编译结束**: 2026-06-10 10:35
**最终状态**: built
