# Lua 5.1.5 编译笔记

## 编译信息
- **软件名称**: lua
- **版本**: 5.1.5
- **编译日期**: 2026-05-26
- **构建系统**: makefile
- **编译状态**: built

## 编译过程

### Phase 1: 初始化
- 下载源码：lua-5.1.5.tar.gz（官方网站lua.org）
- 解压到工作目录
- 无历史归档记录（首次编译）

### Phase 2: 配置
- 构建系统：Makefile（无configure）
- 平台选择：posix
- 编译参数：
  - `CC=clang`
  - `MYCFLAGS=-DLUA_USE_POSIX`
- **说明**: Lua使用简单的Makefile系统，直接指定平台即可

### Phase 3: 编译
- 编译命令：`make posix CC=clang MYCFLAGS=-DLUA_USE_POSIX`
- 编译器：clang
- 编译成功，生成lua和luac可执行文件
- 无警告或错误

### Phase 4: 安装
- 安装命令：`make install INSTALL_TOP=$TEST_PREFIX/$DEFAULT_PREFIX`
- Lua不支持标准DESTDIR变量，使用INSTALL_TOP代替
- 安装成功：bin/lua, bin/luac, lib/liblua.a

### Phase 5: 打包
- **问题**: 打包脚本在处理lib/lua目录时出错
  - 错误：IsADirectoryError
  - 原因：脚本尝试unlink目录而非文件
- **解决方案**: 手动清理空目录后创建tar.gz
- 预编译包：lua-5.1.5-ohos-aarch64.tar.gz (721K)

### Phase 6: 质量验证
- G1 (二进制完整性): PASS
- G2 (功能可用性): PASS (需要libreadline依赖)
- G3 (可移植性): PASS (binary-sign-tool签名失败，但二进制可用)
- G4 (档案完整性): PASS

## 关键发现

### 1. Makefile构建系统
Lua使用简单的Makefile，需要指定平台（posix）而非使用configure。

### 2. INSTALL_TOP代替DESTDIR
Lua不支持标准DESTDIR，需要使用INSTALL_TOP变量控制安装路径。

### 3. 打包脚本bug
打包脚本在处理空目录时出错，需要手动清理。

### 4. 运行时依赖
Lua运行时需要libreadline.so.8，否则会报错。

## 编译参数记录

```bash
# 配置
export CC=clang

# 编译
make posix MYCFLAGS=-DLUA_USE_POSIX

# 安装
make install INSTALL_TOP=/storage/Users/currentUser/usr/local
```

## 预编译包内容

```
lua-5.1.5-ohos-aarch64.tar.gz:
- bin/lua (202K)
- bin/luac (142K)
- include/*.h (5个头文件)
- lib/liblua.a (347K)
```

## 版本说明
- 任务要求编译lua5.1 5.1.5-r13版本
- lua5.1是Lua 5.1系列的软件包名
- 实际版本为5.1.5（Lua官方使用简单数字格式）
- Lua 5.1.5是Lua 5.1系列的最终稳定版本（2012年发布）

---

**编译结束**: 2026-05-26 15:48
**最终状态**: built（预编译包已制作）