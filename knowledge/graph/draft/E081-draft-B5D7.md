# E081 — HMDFS 文件系统不支持 autotools 临时文件操作

## 错误特征
GNU autotools 的 config.status 在执行时报错：
```
./config.status[979]: can't create ./confpg7XfB/subs1.awk: Permission denied
```
或类似临时文件创建失败的错误。

## 触发条件
- 构建系统: **GNU autotools (autoconf)**  
- 阶段: **configuration** (configure → config.status)
- 文件系统: **HMDFS** (HarmonyOS Distributed File System)
- 影响软件: 所有使用 autotools 的项目（MPFR、GMP、openssl、ncurses 等）

## 根因分析
HarmonyOS 的 HMDFS 文件系统不支持 autotools 的临时文件创建操作。config.status 在生成 Makefile 时会创建临时目录（如 `confpg7XfB/`）和临时文件（如 `subs1.awk`），但 HMDFS 对此类操作有权限限制，导致 Permission denied 错误。

这是平台级别的限制，无法通过修改 configure 脚本或源码解决。

## 解决方案

### 推荐方案（优先级 1）
**使用预编译包替代手动编译**（符合 R18 预编译包优先原则）

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- {software} {version}
```

**优势**：
- 预编译包已通过 ELF 签名，可直接执行
- 已处理平台适配问题
- 避免编译链过长浪费时间

### 回退方案（优先级 2）
**使用 CMake 构建系统替代 autotools**（如果软件支持）

```bash
cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX ..
make -j2
make install DESTDIR=$TEST_PREFIX
```

**适用场景**：软件同时提供 autotools 和 CMake 构建选项

### 禁止做法
- ❌ 在 HMDFS 目录（~/tmp、~/builds）下编译 autotools 项目
- ❌ 尝试修改 config.status 或 configure 脚本绕过限制（无法解决）
- ❌ 使用 sudo 或修改权限（HMDFS 是平台限制，权限修改无效）

## 验证
检查当前目录是否在 HMDFS 上：
```bash
df -h ~/tmp | grep hmdfs
# 如果输出包含 hmdfs，则此目录不适合编译 autotools 项目
```

## 关联条目
- 类似: **E002** (/tmp 只读问题)
- 类似: **E052** (ELF 签名需求)
- 相关原则: **R18** (预编译包优先), **R10** (临时文件用 $TMPDIR)

## 影响范围
**所有 GNU autotools 项目**，包括但不限于：
- MPFR
- GMP
- OpenSSL
- ncurses
- readline
- coreutils
- bash
- sed
- gawk
