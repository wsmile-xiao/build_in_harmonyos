# passwdqc 2.1.0 — 编译笔记

## 基本信息

- **软件**: passwdqc 2.1.0
- **构建系统**: 纯 Makefile（非 autotools，无 configure 脚本）
- **下载 URL**: https://www.openwall.com/passwdqc/passwdqc-2.1.0.tar.gz
- **编译器**: clang 15.0.4
- **编译日期**: 2026-06-18

## 编译过程

### 构建系统分析

passwdqc 使用纯 Makefile 构建，无 configure 脚本。Makefile 通过 `uname -s` 检测平台，HarmonyOS 返回 "HarmonyOS"（非 "Linux"），匹配 `*)` fallback 分支。

### 关键决策

1. **PAM 模块跳过**: HarmonyOS 无 PAM 框架（缺 libpam/libcrypt），按 INSTALL 文档使用 `make utils` 仅编译库和命令行工具。
2. **CC 覆盖**: Makefile 默认 CC=gcc，需用 `CC=clang` 覆盖。
3. **安装路径覆盖**: 使用 DESTDIR 模式，覆盖 BINDIR/SHARED_LIBDIR/DEVEL_LIBDIR/INCLUDEDIR/MANDIR/CONFDIR/PKGCONFIGDIR 到 $DEFAULT_PREFIX 下。
4. **passwdqc.pc 生成**: `make utils` 不生成 pkgconfig 文件，需手动 `sed` 从 .in 模板生成。
5. **符号链接修复**: Makefile 的 `SHARED_LIBDIR_REL = ../..$(SHARED_LIBDIR)` 公式在绝对路径时生成错误相对链接，需手动修复为 `libpasswdqc.so.1`。

### 编译命令

```bash
# 构建（仅 utils + library，跳过 PAM）
make utils CC=clang

# 生成 pkgconfig
sed -e 's|@VERSION@|2.1.0|g' passwdqc.pc.in > passwdqc.pc

# Staging 安装
make install_lib install_utils CC=clang DESTDIR=$TEST_PREFIX \
  BINDIR=$DEFAULT_PREFIX/bin \
  SHARED_LIBDIR=$DEFAULT_PREFIX/lib \
  DEVEL_LIBDIR=$DEFAULT_PREFIX/lib \
  INCLUDEDIR=$DEFAULT_PREFIX/include \
  MANDIR=$DEFAULT_PREFIX/share/man \
  CONFDIR=$DEFAULT_PREFIX/etc \
  PKGCONFIGDIR=$DEFAULT_PREFIX/lib/pkgconfig

# 修复 staging 符号链接
rm -f $TEST_PREFIX/$DEFAULT_PREFIX/lib/libpasswdqc.so
ln -s libpasswdqc.so.1 $TEST_PREFIX/$DEFAULT_PREFIX/lib/libpasswdqc.so

# 测试（手动运行，跳过 make check 的 PAM 依赖）
for t in tests/test-*.sh; do bash $t; done
```

## 测试结果

所有 80 个测试全部通过：
- test-pwqcheck-basic.sh: 17 PASS
- test-pwqcheck-length.sh: 19 PASS
- test-pwqcheck-multi.sh: 5 PASS
- test-pwqcheck-similarity.sh: 8 PASS
- test-pwqfilter-mode.sh: 11 PASS
- test-pwqgen.sh: 20 PASS

## 质量门禁

- G1 二进制完整性: PASS (5 ELF 文件)
- G2 功能可用性: PASS-WARN (3 warnings, --version 可用)
- G3 可移植性: PASS-WARN (6 warnings, RPATH/签名)
- G4 档案完整性: PASS

## 二进制验证

```
pwqgen version 2.1.0
pwqcheck version 2.1.0
pwqfilter version 2.1.0
```

功能测试：
- pwqgen 生成密码: `realm$Occur4Haul`
- pwqcheck 检测弱密码: 正确拒绝
- pwqcheck 检测强密码: 正确通过

## 产物

- `packaging/passwdqc-2.1.0-ohos-aarch64.tar.gz` (831KB)
- `packaging/passwdqc-2.1.0-ohos-aarch64-debug.tar.gz` (143KB)

## 知识沉淀

- HarmonyOS 平台 `uname -s` 返回 "HarmonyOS"，passwdqc Makefile 的 case 分支匹配 `*)` fallback，不设置 Linux 加固参数（可接受，无功能影响）
- 无 PAM 框架时使用 `make utils` + `make install_lib install_utils` 替代 `make all` + `make install`
- pkgconfig 文件需手动生成（make utils 不包含 passwdqc.pc 目标）

---

**编译开始**: 2026-06-18
**最终状态**: published
**质量门禁**: PASS
---

**编译结束**: 2026-06-18 19:07
**最终状态**: published
