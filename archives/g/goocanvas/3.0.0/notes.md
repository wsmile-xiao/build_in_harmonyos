# goocanvas 3.0.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-23
- 编译器: clang/clang++（OHOS arm64 交叉编译，clang 15）
- 状态: built

## 编译步骤

```bash
# Conan 配方构建（profile: ohos-aarch64）
conan create archives/g/goocanvas/3.0.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable

# 配方内 configure 参数
./configure --prefix=<prefix> \
  --disable-introspection --disable-python \
  --disable-gtk-doc --disable-gtk-doc-html --disable-gtk-doc-pdf
make -j2
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/config.sub 不识别 `aarch64-unknown-linux-ohos` triplet | GNU autotools 无 HarmonyOS 分支（E007/E298） | 配方内 `_patch_config_sub/_patch_config_guess` 对 configure 树中的 config.sub/config.guess 打 linux-ohos 补丁 |
| 2 | configure 的 config.status 在 HMDFS 临时目录 getcwd 失败 | 沙箱文件系统对工作目录探测受限 | 配方内 `_patch_config_status_tmpdir` 将临时目录迁移至可写路径 |
| 3 | GTK+ 运行时栈在 headless CI 无法加载（libintl 符号缺失） | 无显示服务器 + 运行时库依赖不完整 | test_package 用 dlopen 探测 libgtk-3.so.0 真实可加载性，不可加载时如实跳过冒烟（编译期已链接真实 API 满足 R34） |
| 4 | CI pre-download 把 conandata.yml 就地改写为 file:// 本地缓存路径 | build_and_test.sh 预下载机制 | 提交前恢复为官方 HTTPS 源（download.gnome.org + huaweicloud 镜像） |

## 源码修改

无独立补丁文件；平台适配补丁（config.sub/config.guess linux-ohos、configure tmpdir）以配方内 Python 字符串替换方式实现，已在 manifest 的 `patches_applied` 中说明。

## 依赖版本

- Conan 依赖（已发布制品仓，R35/R36 验证通过）:
  - cairo/1.18.4
  - cairo-gobject/1.18.4
- GTK+3 栈（OHOS 系统前缀 cmd-pkgs 提供，非 Conan）:
  - glib/2.88.0 gdk-pixbuf/2.42.12 atk/2.38.0 fribidi/1.0.13
  - libepoxy/1.5.10 libpng/1.6.43 libjpeg-turbo/3.1.4.1
  - fontconfig/2.16.0 freetype/2.14.3 harfbuzz/14.2.0 pixman/0.46.4
  - pango/1.50.14 zlib/1.3.1 gtk+/3.24.38

## 验证结果

```bash
# W3 本地 CI 模拟（.ci-result.json exit_code=0）
bash ci/conan/build_and_test.sh archives/g/goocanvas/3.0.0
# 结果: Success: 1/1, Pass rate: 100%
# test_package 编译期链接真实 libgoocanvas-3.0（27 个真实 API 断言）
# OHOS 共享库 binary-sign-tool 签名成功（add codesign section）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（Autotools + PkgConfigDeps + 系统 GTK 栈 + 签名） |
| conandata.yml | 官方 HTTPS 源 + sha256 |
| test_package/ | 真实 API 消费者（goo_canvas_group_new/rect_new 等） |
| manifest.yaml | 版本清单（status: built） |

## 注意事项

- 系统 `gtk+-3.0.pc` Requires cairo 与 cairo-gobject，二者必须由 Conan 补齐，否则 pkg-config 探测失败。
- PKG_CONFIG_PATH 顺序：系统前缀 lib/pkgconfig 优先于 Conan generators，避免 conan glib 遮蔽系统 glib。
- OHOS 共享库必须 binary-sign-tool 签名；conanfile package() 内对 .so 逐一签名。
- W4 审计建议（P3 级，后续迭代处理）：cmd-pkgs 下载的 ssl 证书校验可收紧；内联补丁可迁移为 patches/ 独立文件。
