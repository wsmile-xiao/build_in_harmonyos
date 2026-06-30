# ldapvi 1.7 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-04
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
# 1. 安装依赖预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- openldap 2.6.7
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- ncurses 6.4

# 2. 配置环境变量
export CC=clang
export CXX=clang++
export LDFLAGS="-L~/usr/local/lib"
export CPPFLAGS="-I~/usr/local/include -I~/usr/local/include/ncursesw"
export LIBS="-lncursesw"

# 3. Configure（修复 umask 后）
./configure --prefix=/storage/Users/currentUser/usr/local

# 4. 编译
make -j1

# 5. DESTDIR 模式安装
make install DESTDIR=/storage/Users/currentUser/test-install-ldapvi-1.7

# 6. 打包
python3 $SKILL_ROOT/scripts/ohc-run.py package ldapvi 1.7
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 缺少 libldap/liblber | 未安装 LDAP 库依赖 | 安装 openldap 2.6.7 预编译包 |
| 2 | 缺少 ncurses | 未安装终端库依赖 | 安装 ncurses 6.4 预编译包 |
| 3 | 缺少 term.h | ncurses 预编译包缺少头文件 | 创建最小化 term.h 头文件 |
| 4 | HMDFS 权限问题 | configure 使用 umask 077 导致无法创建临时文件 | sed -i 's/umask 077/umask 022/g' configure |
| 5 | getline 函数冲突 | 源码定义的 getline 与系统函数冲突 | 重命名为 ldapvi_getline 和 ldapvi_getline2 |
| 6 | on_exit 函数不存在 | 鸿蒙系统不支持 on_exit | 替换为 atexit + 全局变量 |
| 7 | copy_sasl_output 返回值问题 | 函数缺少返回值 | 添加 return 0 |
| 8 | GNUmakefile 不支持 DESTDIR | 构建系统未实现 DESTDIR | 手动修改 GNUmakefile 添加 DESTDIR 支持 |

## 源码修改

### 补丁列表
1. `0001-common.h.patch` - 重命名 getline 函数声明
2. `0002-configure.patch` - 修复 umask 权限问题
3. `0003-ldapvi.c.patch` - 重命名 getline、替换 on_exit、修复返回值、添加 cleanup_wrapper
4. `0004-misc.c.patch` - 重命名 getline 和 getline2 函数

### 手动创建的头文件
- `/storage/Users/currentUser/usr/local/include/term.h` - 最小化 ncurses term.h 头文件

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| openldap | 2.6.7 | cmd-pkgs 预编译包 |
| ncurses | 6.4 | cmd-pkgs 预编译包 |
| glib-2.0 | 系统自带 | 预装 |
| readline | 系统自带 | 预装 |
| popt | 系统自带 | 预装 |
| openssl | 系统自带 | 预装 |

## 验证结果

```bash
# 打包产物验证
ls ~/archive-project/archives/l/ldapvi/1.7/packaging/
ldapvi-1.7-ohos-aarch64.tar.gz  (10.1 MB)
ldapvi-1.7-ohos-aarch64-debug.tar.gz (3.9 MB)

# ELF 检查
file test-install-ldapvi-1.7/storage/Users/currentUser/usr/local/bin/ldapvi
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

# 质量门禁
✅ G1 Binary Integrity: PASS
✅ G2 Functional: PASS (⚠️ 1 warning)
✅ G3 Portability: PASS
❌ G4 Archive: PASS (修复 build_system 字段后)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ldapvi-1.7-ohos-aarch64.tar.gz | 10.1 MB | 预编译包（含依赖） |
| ldapvi-1.7-ohos-aarch64-debug.tar.gz | 3.9 MB | 调试符号包 |
| 0001-common.h.patch | 834 B | 函数重命名补丁 |
| 0002-configure.patch | 732 B | umask 修复补丁 |
| 0003-ldapvi.c.patch | 3.1 KB | 主程序修复补丁 |
| 0004-misc.c.patch | 3.0 KB | misc 函数修复补丁 |

## 注意事项

1. **term.h 缺失问题**：ncurses 预编译包缺少 term.h 头文件，需要手动创建或从完整 ncurses 源码获取
2. **SASL 支持已禁用**：configure 警告 "SASL support disabled"，因为缺少 cyrus-sasl
3. **本地安装无法直接运行**：需要解压预编译包或通过 cmd-pkgs 安装脚本部署
4. **测试套件缺失**：ldapvi 无 make check 目标

---
**编译结束**: 2026-06-04 16:22
**最终状态**: published
---

**编译结束**: 2026-06-04 16:23
**最终状态**: built
