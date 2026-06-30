# openldap 2.6.9 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-08
- 编译器: clang/clang++
- 状态: **built**（编译成功，已生成预编译包）

## 成功方案：TMPDIR 修复

### 核心问题
HMDFS 文件系统限制 autotools 在当前目录创建临时文件，导致 configure/config.status 失败。

### 解决方案组合
1. **修改 configure**: 将 `mktemp -d "./confXXXXXX"` 改为 `mktemp -d "$TMPDIR/confXXXXXX"`
2. **修改 config.status**: 去掉 `umask 077`（避免临时目录权限过于严格）
3. **禁用 MDB backend**: musl libc 不支持 robust mutex（pthread_mutexattr_setrobust）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 结果 |
|---|------|------|----------|------|
| 1 | config.guess 无法识别平台 | HMDFS 临时文件限制 | 更新 config.guess/config.sub | ✅ 成功 |
| 2 | configure 临时目录创建失败 | HMDFS 限制 ./confXXXXXX | 修改使用 $TMPDIR | ✅ 成功 |
| 3 | config.status 权限问题 | umask 077 导致目录权限过严 | 去掉 umask 077 | ✅ 成功 |
| 4 | pthread_mutexattr_setrobust 缺失 | musl libc 不支持 robust mutex | 禁用 MDB backend (--disable-mdb) | ✅ 成功 |

## 关键补丁

### 0003-configure.patch（核心补丁）
修改 configure 脚本使用 TMPDIR 创建临时目录：
```diff
- ac_tmp=`mktemp -d "./confXXXXXX"`
+ ac_tmp=`mktemp -d "$TMPDIR/confXXXXXX"`
```

### 使用方法
```bash
export TMPDIR="$HOME/tmp/config-tmp"
mkdir -p "$TMPDIR"
./configure --prefix=$DEFAULT_PREFIX --disable-mdb
# config.status 生成后，去掉 umask 077
sed -i 's/umask 077 &&/umask 022 \&\&/' config.status
```

## 编译产物

### 库文件
- liblber.a (104KB) - LDAP 基础编码库
- liblber.so.2.0.200 (76KB)
- libldap.a (649KB) - LDAP 客户端库
- libldap.so.2.0.200 (383KB)

### 客户端工具
- ldapsearch, ldapmodify, ldapadd, ldapdelete
- ldapcompare, ldapexop, ldapmodrdn, ldappasswd
- ldapurl, ldapvc, ldapwhoami

## 知识提取

### E083 - HMDFS autotools config.status 失败
- **根因**: HMDFS SELinux/HMMAC 限制 autotools 在当前目录创建临时文件
- **解决方案**: TMPDIR 方案 + umask 修改
- **适用范围**: 所有 autotools 构建（L1 平台真理）

### E084 - musl libc robust mutex 缺失
- **根因**: musl 不支持 pthread_mutexattr_setrobust
- **解决方案**: 禁用依赖 robust mutex 的功能
- **适用范围**: LMDB、OpenLDAP MDB backend 等

## 验证结果

```bash
# 库验证
ls ~/usr/local/lib/libldap* ~/usr/local/lib/liblber*
# liblber.a, liblber.so, libldap.a, libldap.so

# 质量门禁
G1: PASS（二进制完整性）
G2: PASS（功能可用性）
G3: PASS（可移植性）
G4: PASS（档案完整性）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| openldap-2.6.9-ohos-aarch64.tar.gz | 26MB | 预编译包 |
| openldap-2.6.9-ohos-aarch64-debug.tar.gz | 1.3MB | 调试符号包 |
| 0003-configure.patch | 864B | TMPDIR 修复补丁 |

## 注意事项

1. **TMPDIR 必须设置**: 编译前必须 `export TMPDIR=...`
2. **config.status 需二次修改**: configure 运行后需去掉 umask 077
3. **MDB backend 已禁用**: 无法使用 LMDB 存储（musl 限制）

---

**编译结束**: 2026-06-08 16:17
**最终状态**: built