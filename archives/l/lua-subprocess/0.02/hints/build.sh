#!/bin/sh
# lua-subprocess 构建脚本
# 该软件使用 Makefile 构建系统，没有 configure 步骤

# 设置 PKG_CONFIG_PATH 以找到 Lua
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH

# 设置编译器
export CC=clang

# 直接运行 make（跳过 configure）
make CFLAGS="-Wall -Wextra -pedantic -O2" || exit 1

# 安装到 staging 目录
LUA_INSTALL_CMOD=$(pkg-config --variable=INSTALL_CMOD lua)
mkdir -p $DESTDIR$LUA_INSTALL_CMOD
install -m755 subprocess.so $DESTDIR$LUA_INSTALL_CMOD/ || exit 1

exit 0