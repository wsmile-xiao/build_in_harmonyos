# gtk 3.24.43 适配笔记

## 编译环境
- 构建系统: meson (>=0.60.0, 上游 meson.build)
- 编译日期: 2026-08-21
- 编译器: clang 15.0.4 / clang++ (OHOS aarch64)
- 状态: built (待 conan-verify 后更新为 published)
- 归档: archives/g/gtk/3.24.43 (首字母 g，h 为误判已纠正)
- 分支: feat/gtk-3.24.43 (基于 origin/main)

## 编译步骤

1. **下载源码（官方源 R39）**
   ```bash
   # 主源（GNOME 官方）
   https://download.gnome.org/sources/gtk+/3.24/gtk+-3.24.43.tar.xz  # sha256 7e04f0648515034b806b74ae5d774d87cffb1a2a96c468cb5be476d51bf2f3c7
   # 镜像
   https://repo.huaweicloud.com/gnome/sources/gtk+/3.24/gtk+-3.24.43.tar.xz
   tar xf gtk+-3.24.43.tar.xz  # 上游目录 gtk+-3.24.43，包名 gtk
   ```

2. **Conan 配方（meson + broadway）**
   - `conanfile.py` 为 meson 配方，PkgConfigDeps + MesonToolchain
   - broadway 后端：`-Dx11_backend=false -Dwayland_backend=false -Dbroadway_backend=true`
   - 禁用：xinerama/cloudproviders/profiler/introspection/gtk_doc/man/demos/examples/tests
   - glib 构建工具：按 gdk-pixbuf 模式包装 `glib-mkenums`/`glib-genmarshal` 为 native wrapper，注入 pkg-config 变量

3. **本地验证**
   ```bash
   conan create archives/g/gtk/3.24.43 --version=3.24.43 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
   # test_package 调用 gtk_get_major_version()/gtk_check_version()/gtk_widget_get_type() (R34)
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 误判 build_system=autotools | 上游实际为 meson，_guess_build_system 按 URL 关键词误判 | 手写 meson 配方，manifest 中 build.system=meson 覆盖 |
| 2 | 归档字母误判 h/gtk | 包名 gtk 首字母 g，h 为误判 | 归档 archives/g/gtk/3.24.43，校验 h 目录不存在 |
| 3 | 官方源 URL | 需 R39 认可的官方源 | 主源 download.gnome.org + 华为云镜像 fallback，conandata.yml 声明 |
| 4 | 鸿蒙无 X11/Wayland | 系统无原生显示后端 | broadway HTML5 后端，禁用 X11/Wayland/Quartz/Win32 |
| 5 | epoxy 依赖名称 | meson 依赖名 epoxy，制品仓为 libepoxy/1.5.10 | requirements 中 libepoxy/1.5.10，Meson 通过 pkg_config_name=epoxy 解析 |
| 6 | glib 构建时工具 | glib-mkenums 等为 Python 脚本，需 native 执行 | 复用 gdk-pixbuf 的 wrapper 方案 + PkgConfigDeps 变量注入 |
| 7 | 无补丁 | 平台问题通过 meson 选项解决 | patches: {} 为空，无源码补丁 |

## 源码修改

无补丁，平台适配通过 meson 选项完成（broadway 后端替代 X11/Wayland）。

## 依赖版本

- glib/2.84.0.1 (shared=True OHOS binary 已验证；2.84.0.1.1 因 pango/atk/cairo-gobject/gdk-pixbuf recipe 均 pin 2.84.0.1 未升级)
- cairo/1.18.4, cairo-gobject/1.18.4.2
- pango/1.50.14.1.1（依赖项 PR #6196；旧 1.50.14 绑定 glib 静态，新版本绑定 shared=True）
- gdk-pixbuf/2.44.6.1
- atk/2.38.0.1.1
- fribidi/1.0.16
- libepoxy/1.5.10 (提供 epoxy.pc)
- harfbuzz/14.2.0
- pixman/0.46.4
- freetype/2.14.3
- fontconfig/2.18.1
- libpng/1.6.58
- zlib/1.3.1.1
- expat/2.8.2.1.1

## 验证结果

```bash
# Conan 验证（14 步中 conan-verify）
conan create archives/g/gtk/3.24.43 --version=3.24.43 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 预期: G1-G4 通过，L2 smoke test 调用 gtk_get_major_version 等 API (R34)
pkg-config --modversion gtk+-3.0  # 验证头文件与 pc 文件安装
```

## 交付物

| 文件 | 说明 |
|------|------|
| archives/g/gtk/3.24.43/conanfile.py | Meson 配方（broadway 后端） |
| archives/g/gtk/3.24.43/conandata.yml | 官方源 + sha256 + mirror |
| archives/g/gtk/3.24.43/test_package/* | 真实 API 测试（R34） |
| archives/g/gtk/3.24.43/manifest.yaml | 版本元数据（含依赖与选项） |
| archives/g/gtk/manifest.yaml | 软件级索引 |

## 注意事项

1. **Broadway 后端**: 鸿蒙无 X11/Wayland，需启动 broadwayd 服务通过浏览器访问
2. **动态库签名**: OHOS 共享库需 binary-sign-tool 签名，已在 package() 中处理
3. **深度适配 (R40)**: 图形 UI 框架，需 broadway 适配代码非 stub，meson 选项已实质切换后端；冒烟测试仅覆盖版本/类型注册 API，不初始化显示后端——broadway 运行时行为（gtk_init/broadwayd 会话）**需人工确认适配完整性**（AI 检视 P3，2026-08-21）
---

**编译结束**: 2026-08-21 15:58
**最终状态**: built
