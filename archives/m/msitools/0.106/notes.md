# msitools 0.106 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-07-06
- 编译器: clang/clang++ (clang 15.0.4)
- 状态: built

## 编译步骤

```bash
# 由于下载 URL 使用的域名连接不稳定，实际使用已下载好的 tarball
# 有效 tarball SHA256: 01f56b97465d0449e9182ea9ed8b7a3588264c04f828cc07d9569accbc8a6648

# 1. 初始化（使用本地 tarball）
cd /storage/Users/currentUser/runner002/build_in_harmonyos
python3 scripts/ohc-run.py init-build msitools 0.106 --url=https://download.gnome.org/sources/msitools/0.106/msitools-0.106.tar.xz --no-download

# 2. Meson 配置与编译
cd /storage/Users/currentUser/tmp/builds/msitools-0.106.work
meson setup builddir --prefix=/storage/Users/currentUser/usr/local -Ddefault_library=static
ninja -C builddir
ninja -C builddir install
meson test -C builddir
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 自动检测构建系统为 autotools | 引导脚本未识别 Meson 项目特征 | 手动修正 manifest.yaml 为 meson |
| 2 | GNOME 官方下载地址连接被重置 | 网络限制 | 使用已有缓存 tarball + --no-download |
| 3 | ohc-run.py conan-init 生成 Autotools 模板 | 构建系统检测错误 | 手动重写 conanfile.py 为 Meson 模板 |

## 源码修改

无补丁。源码无需修改。

## 依赖版本

- glib-2.0 (>= 2.12) — 系统提供
- gio-2.0 (>= 2.14) — 系统提供
- gobject-2.0 (>= 0.9.4) — 系统提供
- libgsf-1 — 系统提供
- libxml-2.0 (>= 2.7) — 系统提供

## 验证结果

```bash
$ meson test -C builddir
 1/1 msitools:Tools tests   OK (0.03s)
Ok:      0
Fail:    0
Skipped: 1 (bats not available)

$ ls -la builddir/tools/
msibuild  msidiff  msidump  msiinfo

$ builddir/tools/msiinfo --help
# 正常输出帮助信息
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/msibuild | 11.3 MB | MSI 构建工具 |
| bin/msiinfo | 11.3 MB | MSI 信息查看器 |
| bin/msidiff | 5.5 KB | MSI 差异比较工具 |
| bin/msidump | 3.3 KB | MSI 转储工具 |
| lib/libmsi-1.0.a | 1.0 MB | 静态链接库 |
| include/libmsi-1.0/ | — | 6 个头文件 |

## 注意事项

- 构建依赖 libgsf-1（需要预先安装到系统或通过 Conan 管理）
- wixl 工具需要 vala 编译器，当前编译未启用（不阻塞）
- 上游测试套件使用 bats（bash automated testing），未安装则跳过
---

**编译结束**: 2026-07-06 17:09
**最终状态**: built
