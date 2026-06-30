# lua-resty-hmac v0.06 适配笔记

## 编译环境
- 构建系统: makefile（纯 Lua 库）
- 编译日期: 2026-06-11
- 编译器: N/A（纯 Lua 文件，无需编译）
- 状态: built（编译成功，需要特定运行环境）

## 编译步骤

1. 下载源码：从 GitHub jkeys089/lua-resty-hmac 下载 v0.06
2. 构建依赖：运行 `make all` 下载 lua-resty-string 依赖
3. 手动安装：由于脚本的 PREFIX 不匹配，手动安装到 staging 目录
4. 打包：创建 tar.gz 预编译包
5. 本地安装：安装到 `/usr/local/openresty/lualib/resty/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | URL 搜索失败 | 仓库不在 openresty 组织下 | 手动搜索找到 jkeys089/lua-resty-hmac |
| 2 | PREFIX 不匹配 | 脚本期望 /usr/local，实际需要 /usr/local/openresty | 手动安装到正确路径 |
| 3 | FFI 模块缺失 | 需要 LuaJIT 环境，标准 Lua 5.4 不支持 | 标记为 built，记录限制 |

## 源码修改

无补丁，纯 Lua 文件。

## 依赖版本

- lua-resty-string（自动下载）

## 验证结果

```bash
# 文件已正确安装
ls -lR /storage/Users/currentUser/usr/local/openresty/lualib/resty/
# hmac.lua
# string.lua

# 注意：需要 LuaJIT/OpenResty 环境才能运行
# 标准 Lua 5.4 缺少 FFI 模块
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lua-resty-hmac-v0.06-ohos-aarch64.tar.gz | 10K | 纯 Lua 文件包 |

## 注意事项

1. **运行环境要求**：此库依赖 LuaJIT 的 FFI 模块，只能在 OpenResty 环境中使用
2. **安装路径**：必须安装到 `/usr/local/openresty/lualib/resty/`，不能使用标准 `/usr/local/lib/`
3. **无 ELF 签名需求**：纯 Lua 文件，不需要签名处理
---

**编译结束**: 2026-06-11 12:02
**最终状态**: built
