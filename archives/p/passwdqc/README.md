# passwdqc

密码/口令强度检查与策略强制工具包（Password Quality Control）。

passwdqc 由 Solar Designer 为 Openwall GNU/*/Linux 开发，提供密码质量检查库和命令行工具。

## 组件

| 组件 | 类型 | 说明 |
|------|------|------|
| libpasswdqc.so.1 | 共享库 | 密码质量检查核心库 |
| pwqgen | 命令行工具 | 生成随机可发音密码 |
| pwqcheck | 命令行工具 | 检查密码/口令强度 |
| pwqfilter | 命令行工具 | Bloom 过滤器密码字典查找 |
| pam_passwdqc | PAM 模块 | PAM 集成（HarmonyOS 不构建） |

## 已编译版本

- **2.1.0** (2026-06-22) — published

## 构建说明

passwdqc 使用纯 Makefile 构建（非 autotools），无 configure 脚本。

### HarmonyOS 编译

```bash
# 构建库+工具（跳过PAM模块）
make utils CC=clang

# 生成 pkgconfig 文件（make utils 不包含此目标）
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

# 修复符号链接（Makefile 的 SHARED_LIBDIR_REL 公式在绝对路径下生成错误链接）
rm -f $TEST_PREFIX/$DEFAULT_PREFIX/lib/libpasswdqc.so
ln -s libpasswdqc.so.1 $TEST_PREFIX/$DEFAULT_PREFIX/lib/libpasswdqc.so
```

### 平台适配要点

1. HarmonyOS 的 `uname -s` 返回 "HarmonyOS"，匹配 Makefile 的 `*)` fallback 分支
2. 无 PAM 框架，使用 `make utils` 替代 `make all`
3. CC 需覆盖为 clang（Makefile 默认 gcc）
4. pkgconfig 文件需手动生成
5. 符号链接需手动修复
