# Notes — libecpg 18.3

## 软件说明
libecpg 是 PostgreSQL 的嵌入式 SQL (ECPG) 预处理器和库。源码来自 PostgreSQL 18.3 完整包，只编译 src/interfaces/ecpg 子目录。

## 编译日期
2026-06-03

## 修复记录

### E072: config.sub/config.guess 三元组验证失败

**问题**: HarmonyOS (uname -s = "HarmonyOS") 不被标准 config.guess/config.sub 识别。

**修复**:
1. **config/config.guess**:
   - 添加 `HarmonyOS)` 到 `case $UNAME_SYSTEM in` 分支，设置 LIBC=ohos, UNAME_SYSTEM=Linux
   - 添加 `#if defined(__OHOS__) LIBC=ohos` 到 LIBC 编译检测
   - 修复 HMDFS mktemp 权限问题：去掉 umask 077，改用 mktemp -d + chmod 755 和 mkdir -m 755
2. **config/config.sub**:
   - 添加 `ohos-linux)` basic_os 映射（修改1）
   - OS 白名单已有 `| ohos*`（修改2）
   - kernel-os 白名单已有 `| linux-ohos*-`（修改3）
3. **configure**:
   - 修复 HMDFS mktemp 权限问题（去掉 umask 077，添加 chmod 755）

### E002/HMDFS: mktemp 目录权限问题

**问题**: `umask 077 && mktemp -d` 在 HMDFS 上创建的目录权限为 drwx--S---，即使 chmod 755 也无法写入文件。
**修复**: 去掉 umask 077，改用 mktemp -d（不加 umask）+ chmod 755，或直接用 mkdir -m 755。
**根因**: HMDFS 文件系统对 umask 077 创建的目录有特殊限制。

## Configure 参数
```
--prefix=/storage/Users/currentUser/usr/local
--without-icu --without-readline --without-zstd --without-lz4
--without-gssapi --without-ldap --without-pam
--with-openssl --with-zlib
CC=clang CFLAGS="-fPIC -O2"
LDFLAGS="-L/storage/Users/currentUser/usr/local/lib"
CPPFLAGS="-I/storage/Users/currentUser/usr/local/include -D_GNU_SOURCE"
CXX=clang++ CXXFLAGS="-fPIC -O2"
```

## 测试说明
ECPG 回归测试需要运行 PostgreSQL 服务器，无法在当前构建环境执行。测试程序编译验证通过。

## 依赖
- PostgreSQL 源码内部依赖: libpq, libpgcommon, libpgport (同源编译)
- 外部依赖: OpenSSL (libssl/libcrypto), zlib

## 功能测试记录 (2026-06-03 补充)

### ECPG 预处理器测试

| 测试项 | 结果 |
|--------|------|
| ecpg --version | ✅ 输出 "ecpg (PostgreSQL) 18.3" |
| ecpg --help | ✅ 正确输出帮助信息 |
| ECPG DECLARE SECTION (int/char) | ✅ 正确转换为 C 变量声明 |
| ECPG -c 模式 | ✅ 正确处理自动代码生成 |
| ECPG -C INFORMIX 模式 (简化类型) | ✅ 正确处理 decimal/interval |
| ECPG -C INFORMIX (限定 interval) | ❌ "syntax error at or near 'to'" |
| ECPG -h 头文件模式 | ✅ 正确处理 .pgh 文件 |
| ECPG SQL CONNECT 转换 | ✅ ECPGconnect() 正确生成 |
| pkg-config --modversion | ✅ 全部返回 "18.3" |

### 运行时库链接测试（修复后验证）

| 测试项 | 结果 |
|--------|------|
| 动态链接 ECPG 程序编译 | ✅ PASS — ecpg → C → binary 全流程成功 |
| ECPG SQL 程序运行 | ✅ PASS — exit code 0 |
| libecpg/libpgtypes 运行时 | ✅ PASS — numeric=42, date=2026-06-03 |
| 静态链接 libpgtypes.a | ✅ PASS — libpgport/libpgcommon 已安装 |

### 打包完整性测试（修复后验证）

| 测试项 | 结果 |
|--------|------|
| libpq.so.5 在 lib/external/ | ✅ 已包含（+ libssl.so.1.1, libcrypto.so.1.1） |
| libpq-fe.h 在 ~/usr/local/include | ✅ 已安装（从 PostgreSQL 18.3 源码同源） |
| pkg-config prefix 可移植性 | ⚠️ 硬编码本地路径（cmd-pkgs 安装脚本会修正） |
| ELF 签名 (.note.ohos.ident) | ✅ 正常 |

### 修复记录

1. **libpq.so.5 缺失** → `ohc-run.py package` 重新打包，自动收集 libpq.so.5 + libssl + libcrypto 到 lib/external/
2. **libpq-fe.h 缺失** → 从 PostgreSQL 18.3 构建目录同源安装到 ~/usr/local/include
3. **libpgport/libpgcommon 缺失** → 从构建目录安装 libpgport.a + libpgcommon.a 到 ~/usr/local/lib

### 上库评估

**✅ 符合上库要求** — 所有阻塞问题已修复：
- 运行时依赖：打包产物 lib/external/ 包含 libpq.so.5 + libssl + libcrypto
- 编译时依赖：libpq 预编译包提供头文件和链接器名称
- 静态库依赖：libpgport.a + libpgcommon.a 已安装到 ~/usr/local/lib

**用户安装流程**：先安装 libpq（提供开发头文件）→ 再安装 libecpg（包含运行时依赖）

---

**编译结束**: 2026-06-03 10:31
**打包修复**: 2026-06-03 15:42
**最终状态**: built ✅ (阻塞问题已修复，可升级为 published)
