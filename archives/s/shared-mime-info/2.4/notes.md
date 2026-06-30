# shared-mime-info 2.4 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从清华镜像下载源码包 shared-mime-info_2.4.orig.tar.bz2
2. 使用 meson 配置构建，禁用 build-tools（因为缺少 libxml2 和 glib 依赖）:
   ```
   meson setup build --prefix=$HOME/usr/local \
     -Dbuild-tools=false \
     -Dbuild-translations=true \
     -Dbuild-tests=false \
     -Dupdate-mimedb=false
   ```
3. 编译: ninja -C build
4. 安装到 staging: ninja -C build install (DESTDIR 模式)
5. 安装到本地: ninja -C build install
6. 制作预编译包: ohc-run.py package

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无法从 GitLab 下载源码 | SSL 证书问题 + 网络超时 | 使用清华镜像 https://mirrors.tuna.tsinghua.edu.cn |
| 2 | 缺少 libxml-2.0 和 glib-2.0 依赖 | 系统未安装预编译包，网络问题无法安装 | 禁用 build-tools 只安装 MIME 数据库 |
| 3 | manifest 验证失败 | 验证脚本检查顶层 build_system 字段 | 添加顶层 build_system: meson 字段 |

## 源码修改

无补丁。源码无需修改即可编译。

## 依赖版本

- meson: 1.11.1
- xmllint: libxml 21109
- gettext (msgfmt/msginit/msgmerge/xgettext): 已安装

## 验证结果

```bash
# 检查安装的 MIME 数据库
ls -lh ~/usr/local/share/mime/packages/freedesktop.org.xml
# -rw-r----- 2.3M freedesktop.org.xml

# 检查 pkg-config 文件
cat ~/usr/local/share/pkgconfig/shared-mime-info.pc
# prefix=/storage/Users/currentUser/usr/local
# Name: shared-mime-info
# Version: 2.4
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| shared-mime-info-2.4-ohos-aarch64.tar.gz | 4.6M | 预编译包（MIME 数据库 + 翻译） |

## 注意事项

1. 本次编译禁用了 build-tools，只安装 MIME 数据库文件。如果需要 update-mime-database 工具，需要先安装 libxml2 和 glib 预编译包。
2. shared-mime-info 是 meson 项目而非 autotools，需使用 meson configure。
3. 网络问题严重时建议使用国内镜像（清华/阿里云）。
---

**编译结束**: 2026-05-28 11:00
**最终状态**: built
