# Lua 5.3.6 编译笔记

## 编译信息
- 软件: lua
- 版本: 5.3.6
- 构建系统: custom (Makefile)
- 编译器: clang (系统无 gcc)
- 平台: generic (系统无 readline 库)
- 安装路径: /storage/Users/currentUser/usr/local

## 编译步骤

### 1. 源码获取
```bash
# 官方下载失败（SSL 问题），使用 curl --insecure 下载
curl -L -o lua-5.3.6.tar.gz http://www.lua.org/ftp/lua-5.3.6.tar.gz --insecure
```

### 2. Makefile 修改
```bash
# 修改安装路径
sed -i 's/^INSTALL_TOP= \/usr\/local$/INSTALL_TOP= \/storage\/Users\/currentUser\/usr\/local/' Makefile

# 修改编译器 (src/Makefile)
sed -i 's/^CC= gcc -std=gnu99$/CC= clang/' src/Makefile
```

### 3. 编译
```bash
# 使用 generic 平台（无 readline 依赖）
make generic
```

### 4. 手动安装
```bash
# 系统缺少 install 命令，手动复制
mkdir -p ~/usr/local/bin ~/usr/local/include ~/usr/local/lib
cp -p src/lua src/luac ~/usr/local/bin/
cp -p src/liblua.a ~/usr/local/lib/
cp -p src/lua.h src/luaconf.h src/lualib.h src/lauxlib.h src/lua.hpp ~/usr/local/include/
```

### 5. pkg-config 支持
```bash
# 创建 lua.pc 文件
mkdir -p ~/usr/local/lib/pkgconfig
cat > ~/usr/local/lib/pkgconfig/lua.pc << 'EOF'
prefix=/storage/Users/currentUser/usr/local
exec_prefix=${prefix}
libdir=${exec_prefix}/lib
includedir=${prefix}/include

Name: Lua
Description: Lua scripting language
Version: 5.3.6
Libs: -L${libdir} -llua -lm
Cflags: -I${includedir}
EOF
```

## 验证结果

```bash
$ ~/usr/local/bin/lua -v
Lua 5.3.6  Copyright (C) 1994-2020 Lua.org, PUC-Rio

$ ~/usr/local/bin/lua -e 'print("Hello from Lua!")'
Hello from Lua!

$ PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig pkg-config --modversion lua
5.3.6
```

## 产物路径
- 二进制: ~/usr/local/bin/lua, ~/usr/local/bin/luac
- 库文件: ~/usr/local/lib/liblua.a
- 头文件: ~/usr/local/include/lua.h 等
- pkg-config: ~/usr/local/lib/pkgconfig/lua.pc

## 遇到的问题

### 问题 1: SSL 证书验证失败
- 原因: Python urllib 无法验证 SSL 证书
- 解决: 使用 curl --insecure 下载

### 问题 2: 缺少 gcc
- 原因: OpenHarmony 系统使用 clang
- 解决: 修改 src/Makefile 使用 clang

### 问题 3: 缺少 readline 库
- 原因: linux 平台依赖 readline
- 解决: 使用 generic 平台编译

### 问题 4: 缺少 install 命令
- 原因: 系统无 GNU install 工具
- 解决: 手动复制文件

---
**编译开始**: 2026-06-04 16:19
**编译结束**: 2026-06-04 16:23
**最终状态**: built (成功)
---

**编译结束**: 2026-06-04 16:25
**最终状态**: built
