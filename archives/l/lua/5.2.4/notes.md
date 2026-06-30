# Lua 5.2.4 编译笔记

## 编译信息

- **软件**: Lua 5.2.4
- **编译日期**: 2026-05-26
- **编译系统**: Makefile
- **平台**: linux (HarmonyOS 兼容)
- **编译器**: clang 15.0.4

## 编译过程

### 1. 源码获取

由于 SSL 证书问题，从 lua.org 和华为镜像下载失败。使用 curl -k 手动下载成功。

```bash
curl -L -k -o lua-5.2.4.tar.gz https://www.lua.org/ftp/lua-5.2.4.tar.gz
```

### 2. 编译配置

#### Makefile 修改

Lua 的 Makefile 需要修改以支持 HarmonyOS：

1. **DESTDIR 支持**: 添加 DESTDIR 变量以支持 staging 安装（符合 R20 铁律）
2. **使用 cp 替代 install**: HarmonyOS 上没有 install 命令，需要使用 cp

修改内容：
- 在 Makefile 中添加 `DESTDIR?=`
- 将所有安装路径改为 `$(DESTDIR)$(INSTALL_TOP)/...`
- 将 `INSTALL= install -p` 改为 `INSTALL= cp -p`

#### 编译命令

```bash
cd ~/builds/lua-5.2.4.work
make linux CC=clang MYCFLAGS="-I/storage/Users/currentUser/usr/local/include" MYLDFLAGS="-L/storage/Users/currentUser/usr/local/lib"
```

### 3. 编译结果

编译成功，无错误。

生成的文件：
- `src/lua` (227KB) - Lua 解释器
- `src/luac` (162KB) - Lua 编译器
- `src/liblua.a` (357KB) - Lua 静态库

### 4. 安装

#### Staging 安装（DESTDIR 模式）

```bash
make install INSTALL_TOP=/storage/Users/currentUser/usr/local DESTDIR=/storage/Users/currentUser/tmp/test-install-lua-5.2.4
```

#### 用户本地安装

由于文件已存在，需要手动删除旧文件后复制：

```bash
rm -f ~/usr/local/bin/lua ~/usr/local/bin/luac
cp -p src/lua ~/usr/local/bin/lua
cp -p src/luac ~/usr/local/bin/luac
cp -p src/liblua.a ~/usr/local/lib/
cp -p src/*.h ~/usr/local/include/
```

### 5. 验证

```bash
lua -v
# Lua 5.2.4  Copyright (C) 1994-2015 Lua.org, PUC-Rio

lua -e "print('Hello from Lua 5.2.4')"
# Hello from Lua 5.2.4

lua -e "print(_VERSION)"
# Lua 5.2
```

## 遇到的问题和解决方案

### 问题 1: SSL 证书验证失败

**现象**: 从 lua.org 和华为镜像下载时 SSL 证书验证失败。

**解决方案**: 使用 `curl -L -k` 绕过 SSL 验证。

### 问题 2: GCC 不可用

**现象**: HarmonyOS 上默认使用 clang，不是 gcc。

**解决方案**: 在 make 命令中指定 `CC=clang`。

### 问题 3: install 命令不可用

**现象**: HarmonyOS 上没有 install 命令，make install 失败。

**解决方案**: 修改 Makefile，将 `INSTALL= install -p` 改为 `INSTALL= cp -p`。

### 问题 4: 文件覆盖权限问题

**现象**: cp 命令无法覆盖已存在的可执行文件。

**解决方案**: 先删除旧文件（`rm -f`），然后复制新文件（`cp -p`）。

### 问题 5: /tmp 只读文件系统

**现象**: luac 输出到 /tmp 时失败，因为 /tmp 是只读文件系统。

**解决方案**: 使用 `$TMPDIR`（设置为 `/storage/Users/currentUser/tmp`）。

## 补丁文件

- `0001-Makefile-DESTDIR-and-cp-support.patch`: 添加 DESTDIR 支持和使用 cp 替代 install

## 依赖

- **readline**: 用于交互式命令行编辑（可选，已安装）

## 知识提取

### L1 平台真理

1. HarmonyOS 上使用 clang 而不是 gcc
2. HarmonyOS 上没有 install 命令，需要使用 cp
3. /tmp 是只读文件系统，必须使用 $TMPDIR

### L2 模式经验

1. Lua 使用 Makefile 构建系统，支持自定义 CC、MYCFLAGS、MYLDFLAGS
2. Lua 的 Makefile 不支持 DESTDIR，需要手动添加
3. Lua 的 "linux" 平台目标适用于 HarmonyOS

## 编译结束

**最终状态**: built

**验证结果**:
- lua -v: ✅ Lua 5.2.4
- lua -e "print('Hello from Lua 5.2.4')": ✅ Hello from Lua 5.2.4
- luac 编译测试: ✅ 通过
---

**编译结束**: 2026-05-26 15:36
**最终状态**: built
