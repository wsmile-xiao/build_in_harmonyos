# lua-pc 5.4.7 适配笔记

## 编译环境
- 构建系统: makefile (custom)
- 编译日期: 2026-06-12
- 编译器: clang
- 状态: built

## 编译步骤

1. 使用 Lua 官方源码 lua-5.4.7.tar.gz
2. 使用 `make linux CC=clang MYCFLAGS="-Wno-unused-but-set-variable"` 编译
3. 修改 Makefile 中的 INSTALL 命令（从 `install -p` 改为 `cp -p`），因为鸿蒙系统缺少 `install` 命令
4. 安装到 staging 目录: `make install INSTALL_TOP=/storage/Users/currentUser/test-install-lua-pc-5.4.7/usr/local`
5. 重新组织 staging 目录结构以符合 ohc-run.py package 的要求

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | 鸿蒙系统 CA 证书配置问题 | 使用 curl -k 或 file:// URL |
| 2 | 缺少 install 命令 | 鸿蒙系统未提供 GNU install | 修改 Makefile 使用 cp -p |
| 3 | 无法执行未签名 ELF | 鸽蒙安全机制要求 ELF 签名 | 需要在打包时签名 |

## 源码修改

修改 Makefile (顶层):
```diff
- INSTALL= install -p
+ INSTALL= cp -p
```

此修改不会影响运行时路径，因为 Lua 不生成配置文件。

## 依赖版本

- 无外部依赖（Lua 是自包含的）

## 验证结果

```bash
# 编译产物
ls -lh test-install-lua-pc-5.4.7/usr/local/bin/
lua   290K  (Lua 解释器)
luac  214K  (Lua 编译器)
liblua.a  443K  (静态库)

# 本地验证（签名后）
/storage/Users/currentUser/usr/local/bin/lua -v
Lua 5.4.7  Copyright (C) 1994-2024 Lua.org, PUC-Rio
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lua-pc-5.4.7-ohos-aarch64.tar.gz | 1.0M | 预编译包（包含 bin/lua, bin/luac, lib/liblua.a, include/*.h） |
| lua-pc-5.4.7-ohos-aarch64-debug.tar.gz | 120K | 调试符号包 |

预编译包路径: `/storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/archives/l/lua-pc/5.4.7/packaging/lua-pc-5.4.7-ohos-aarch64.tar.gz`

## 注意事项

1. Lua 使用自定义 Makefile，不支持标准的 DESTDIR 模式
2. 需要手动调整 staging 目录结构
3. 编译成功但测试需要在签名后执行
---

**编译结束**: 2026-07-15 23:49
**最终状态**: built
