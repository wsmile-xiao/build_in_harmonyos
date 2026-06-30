# pacman 7.1 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-06-09
- 编译器: /data/service/hnp/bin/clang (OHOS SDK clang 15.0.4 wrapper)
- 状态: published
- 特性: GPGME 签名支持已启用

## 编译步骤

```bash
# 1. 安装 GPGME 依赖（启用签名功能）
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libgpg-error 1.55
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- gpgme 1.24.0

# 2. 配置 meson（启用 GPGME）
cd /storage/Users/currentUser/tmp/builds/pacman-7.1.work
CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++ \
  PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig \
  /storage/Users/currentUser/.opendesk/interpreters/pip-global/bin/meson setup builddir \
  --prefix=/storage/Users/currentUser/usr/local \
  -Dgpgme=enabled

# 3. 编译（需手动修复 libintl_glib 链接）
cd builddir
sed -i 's/-lintl/-lintl_glib/g' build.ninja
/data/service/hnp/bin/ninja -j2

# 4. 安装到 staging
rm -rf /storage/Users/currentUser/tmp/test-install-pacman-7.1
/storage/Users/currentUser/.opendesk/interpreters/pip-global/bin/meson install -C builddir --destdir /storage/Users/currentUser/tmp/test-install-pacman-7.1

# 5. 制作预编译包
python3 $SKILL_ROOT/scripts/ohc-run.py package pacman 7.1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | libintl 符号未定义 | libintl.h 将 dgettext 重定义为 g_libintl_dgettext | 创建 intl.pc 链接 libintl_glib.so |
| 2 | libcurl.pc 含 -l:libunwind.a | 错误依赖声明 | 编辑 libcurl.pc 移除该依赖 |
| 3 | meson 缓存旧依赖 | intl.pc 更新后 meson 未刷新 | 手动编辑 build.ninja 替换 -lintl → -lintl_glib |
| 4 | 缺少 liblzma.so.5 | libarchive 依赖未打包 | 从预编译包复制 liblzma.so.5 |
| 5 | GPGME 未启用 | 缺少 gpgme 依赖 | 安装 gpgme 1.24.0 + libgpg-error 1.55 预编译包 |
| 6 | man pages 构建失败 | asciidoc Python 模块路径问题 | OHOS 平台限制，非关键功能，跳过 |

## 源码修改

无需补丁，所有问题通过 pkg-config 配置、build.ninja 编辑和预编译包安装解决。

## 依赖版本

| 软件 | 版本 | 用途 |
|------|------|------|
| openssl | 3.4.0 | 签名验证 |
| curl | 8.14.1 | 网络下载 |
| libarchive | 3.7.4 | 包解压 |
| gettext | 0.22.5 | 国际化 (libintl_glib) |
| xz | 5.6.3 | lzma 压缩 |
| gpgme | 1.24.0 | GPG 签名支持 |
| libgpg-error | 1.55 | GPGME 依赖 |

## 验证结果

质量门禁全部通过:
- G1 二进制完整性: PASS
- G2 功能可用性: PASS
- G3 可移植性: PASS
- G4 档案完整性: PASS

GPGME 验证:
- config.h: `#define HAVE_LIBGPGME` ✅
- libalpm.so 依赖: `libgpgme.so.11` ✅

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| pacman-7.1-ohos-aarch64.tar.gz | 10.7MB | 预编译包（含 GPGME） |
| pacman-7.1-ohos-aarch64-debug.tar.gz | 3.6MB | 调试符号包 |

## 注意事项

1. ✅ **GPGME 已启用** - 包签名验证功能可用
2. ⚠️ **man pages 未构建** - 因 OHOS Python 环境路径限制，用户可通过在线文档获取帮助
3. 用户安装需确保 libcurl, libssl, libintl_glib, libgpgme 运行时可用
4. makepkg 脚本依赖 bash，需系统预装 GNU bash

---
**编译结束**: 2026-06-09 15:55
**最终状态**: published
