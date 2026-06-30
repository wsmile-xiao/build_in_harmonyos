# lua-lsqlite3 0.9.4 适配笔记

## 编译环境
- 构建系统: makefile (手动创建 Makefile.ohos)
- 编译日期: 2026-06-15
- 编译器: clang/clang++ 15.0.4
- 状态: built (部分成功，动态模块无法加载)

## 编译步骤

1. 源码下载：使用 GitHub API URL（官方 Savannah URL 返回 404）
   ```
   https://api.github.com/repos/slanska/lsqlite3/tarball/master
   ```

2. 原始 Makefile 依赖 luarocks 工具（未安装），需要手动创建编译脚本

3. 创建 Makefile.ohos 手动编译所有模块：
   - lsqlite3.so: 链接外部 sqlite3 库
   - lsqlite3complete.so: 内嵌 sqlite3 3.24.0
   - liblsqlite3complete.a: 静态库

4. 编译命令：
   ```bash
   make -f Makefile.ohos all
   ```

5. 安装到 staging 目录：
   ```bash
   cp -f lsqlite3.so lsqlite3complete.so ~/test-install-lua-lsqlite3-0.9.4/usr/local/lib/lua/5.4/
   cp -f liblsqlite3complete.a ~/test-install-lua-lsqlite3-0.9.4/usr/local/lib/
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 官方 URL 404 | Savannah 仓库不存在或 URL 格式错误 | 使用 GitHub API URL 下载 |
| 2 | Makefile 依赖 luarocks | luarocks 未安装 | 手动创建 Makefile.ohos |
| 3 | SQLite3 未安装 | lua-lsqlite3 需要外部 sqlite3 库 | 安装预编译包 sqlite3 3.49.1 |
| 4 | Lua 不支持动态加载 | OpenHarmony 无 libdl 库 | 创建静态库供自定义 Lua 使用 |

## 源码修改

创建了自定义 Makefile.ohos（位于 ~/builds/lua-lsqlite3-0.9.4.work/）

## 依赖版本

- Lua 5.4.7 (已安装)
- SQLite3 3.49.1 (预编译包)
- clang 15.0.4

## 验证结果

```bash
# 编译产物检查
$ file ~/test-install-lua-lsqlite3-0.9.4/usr/local/lib/lua/5.4/lsqlite3.so
ELF shared object, 64-bit LSB arm64, not stripped

$ lua -e "require 'lsqlite3'"
dynamic libraries not enabled; check your Lua installation
```

⚠️ 运行时限制：OpenHarmony Lua 不支持动态加载模块

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lsqlite3.so | 72KB | 动态模块（链接外部 sqlite3） |
| lsqlite3complete.so | 973KB | 动态模块（内嵌 sqlite3） |
| liblsqlite3complete.a | 1.1MB | 静态库（内嵌 sqlite3） |
| lua-lsqlite3-0.9.4-ohos-aarch64.tar.gz | 2.1MB | 预编译包 |

## 注意事项

**平台限制**: OpenHarmony 无 libdl 库，Lua 不支持动态加载 .so 模块。
用户需要将静态库 liblsqlite3complete.a 链接到自定义 Lua 解释器中使用。

**后续优化**: 如需完整功能支持，需要：
1. 为 OpenHarmony 编译 libdl 库
2. 重新编译 Lua 启用动态加载 (-DLUA_USE_DLOPEN)
3. 重新编译 lua-lsqlite3

---
**编译结束**: 2026-06-15 15:28
**最终状态**: built (编译成功，运行时受限)
---

**编译结束**: 2026-06-15 15:31
**最终状态**: built
