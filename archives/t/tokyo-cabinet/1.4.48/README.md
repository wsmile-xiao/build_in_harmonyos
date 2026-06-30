# tokyo-cabinet 1.4.48 for HarmonyOS

## 概述

tokyo-cabinet 在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南和测试记录。

Tokyo Cabinet 是一个现代的 DBM（数据库管理器）实现，提供高效的键值存储功能，支持哈希数据库、B+树数据库、定长数据库等多种存储模式。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | tokyo-cabinet |
| 版本 | 1.4.48 |
| 下载地址 | https://deb.debian.org/debian/pool/main/t/tokyocabinet/tokyo-cabinet_1.4.48.orig.tar.gz |
| 官方文档 | http://fallabs.com/tokyocabinet/ |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.11.0 |
| 架构 | aarch64 |
| 编译器 | clang (LLVM) |
| 构建系统 | autotools |

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| bzip2 | 1.0.8 | 压缩库支持 |

## 编译步骤

```bash
# 1. 下载源码
wget https://deb.debian.org/debian/pool/main/t/tokyocabinet/tokyo-cabinet_1.4.48.orig.tar.gz
tar -xzf tokyo-cabinet_1.4.48.orig.tar.gz
cd tokyocabinet-1.4.48

# 2. 应用补丁
sed -i 's/umask 077/umask 022/g' configure

# 3. 配置
export CC=clang
export CFLAGS="-fPIC -O2"
export CPPFLAGS="-I$HOME/usr/local/include"
export LDFLAGS="-L$HOME/usr/local/lib"
./configure --prefix=$HOME/usr/local

# 4. 编译
make -j$(nproc)

# 5. 安装
make install

# 6. 签名（OpenHarmony必需）
# 签名所有 ELF 文件
for f in $HOME/usr/local/bin/tc*; do
  ohc-run.py sign-elf "$f"
done
ohc-run.py sign-elf $HOME/usr/local/lib/libtokyocabinet.so.9.11.0

# 7. 修复符号链接（HMDFS不支持软链接）
cd $HOME/usr/local/lib
rm libtokyocabinet.so libtokyocabinet.so.9
cp libtokyocabinet.so.9.11.0 libtokyocabinet.so.9
cp libtokyocabinet.so.9.11.0 libtokyocabinet.so
```

## 补丁说明

### 0001-fix-hmdfs-umask.patch

**目的**: 解决 HMDFS 文件系统的 umask 权限问题

**修改文件**:
- `configure`: 修改临时目录创建的 umask 值

**关键修改详解**:

```diff
- tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`
-   (umask 077 && mkdir "$tmp")
+ tmp=`(umask 022 && mktemp -d "./confXXXXXX") 2>/dev/null`
+   (umask 022 && mkdir "$tmp")
```

**原因**: HMDFS 的 UID 映射机制导致 umask 077 创建的目录权限为 700，但属于不同的 UID，当前进程无法写入，导致 config.status 失败。

## 遇到的问题

### 问题1: configure 失败 - Permission denied

**现象**:
```
./config.status: line 579: ./confXXXX/subs1.awk: Permission denied
```

**原因**: HMDFS 文件系统 UID 映射问题，umask 077 创建的临时目录无法被当前进程访问

**解决**: 修改 configure 脚本中的 `umask 077` 为 `umask 022`

### 问题2: 符号链接不支持

**现象**:
```
ln -s libtokyocabinet.so.9.11.0 libtokyocabinet.so.9
# 符号链接创建成功但运行时找不到库
```

**原因**: HMDFS 不支持符号链接功能

**解决**: 使用 `cp` 复制文件替代 `ln -s` 符号链接

### 问题3: ELF 文件无法执行

**现象**:
```
Error loading shared library libtokyocabinet.so.9
```

**原因**: OpenHarmony 要求 ELF 文件必须签名

**解决**: 使用签名工具对所有可执行文件和共享库签名

## 测试结果

详见 [test-report.md](./reports/test-report.md)

| 测试项 | 结果 |
|--------|------|
| 版本检查 | ✅ |
| HDB 哈希数据库 | ✅ create/put/get/list/out |
| BDB B+树数据库 | ✅ create/put/get/list |
| FDB 定长数据库 | ✅ create/put/get/list |
| 编码工具 | ✅ |

## 验证安装

```bash
# 设置库路径
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH

# 检查安装
ls -la $HOME/usr/local/lib/libtokyocabinet*
ls -la $HOME/usr/local/include/tc*.h
ls -la $HOME/usr/local/bin/tc*

# 检查功能
$HOME/usr/local/bin/tcamgr version
# 输出: Tokyo Cabinet version 1.4.48 (911:1.0) for Linux

# 测试数据库操作
$HOME/usr/local/bin/tchmgr create test.hdb
$HOME/usr/local/bin/tchmgr put test.hdb key1 value1
$HOME/usr/local/bin/tchmgr get test.hdb key1
# 输出: value1
```

## 安装产物

### 库文件
- `libtokyocabinet.a` - 静态库 (896KB)
- `libtokyocabinet.so.9.11.0` - 共享库 (715KB)

### 头文件
- `tcutil.h` - 工具函数
- `tchdb.h` - 哈希数据库
- `tcbdb.h` - B+树数据库
- `tcfdb.h` - 定长数据库
- `tctdb.h` - 表数据库
- `tcadb.h` - 抽象数据库

### 可执行文件
- `tcamgr` - 抽象数据库管理器
- `tchmgr` - 哈希数据库管理器
- `tcbmgr` - B+树数据库管理器
- `tcfmgr` - 定长数据库管理器
- `tctmgr` - 表数据库管理器
- `tcucodec` - 编码工具

## 经验总结

1. **HMDFS 权限问题**: 修改 umask 077 为 umask 022 可解决临时目录权限问题
2. **符号链接替代**: HMDFS 不支持软链接，使用文件复制替代
3. **ELF 签名必需**: OpenHarmony 平台所有 ELF 文件必须签名才能执行
4. **补丁固化修改**: 所有手动修改应创建补丁文件固化，便于后续复用

## 参考资料

- Tokyo Cabinet 官方文档: http://fallabs.com/tokyocabinet/
- HMDFS 文件系统问题参考: E011 (知识库)
- OpenHarmony 编译指南: CONTRIBUTING.md