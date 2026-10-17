# qpdfview

qpdfview 是一个基于 Qt5 + poppler 的**标签页式文档查看器**，支持 PDF（以及可选的
PostScript / DjVu / 图像）文档的浏览、检索、缩放、大纲与文本抽取。

- 上游：<https://launchpad.net/qpdfview>（Launchpad 托管，GPL-2.0-or-later）
- 本仓适配版本：**0.5.0**（HarmonyOS PC / aarch64-linux-ohos）
- 构建系统：**qmake**（顶层 `qpdfview.pro` 为 `TEMPLATE = subdirs`）

## 功能概述

- 标签页式多文档浏览（PDF 为默认后端，poppler 渲染）
- 文本抽取与全文检索（poppler `TextOutputDev` / `Page::search`）
- 页面渲染（`Page::render`，可变 DPI / 旋转）
- 书签、大纲、链接、演示模式、可选唯一实例
- 插件式后端：`pdf` / `ps` / `djvu` / `image` 各自独立 `.so` 插件

## OHOS 适配

### 关键要点

- **内嵌 poppler-qt5 静态绑定**：制品仓 `poppler/25.12.0.2` 为 `ENABLE_QT5=OFF`，
  只安装 C++/glib API，且**没有**独立的 `poppler-qt5` 配方；按 W0/PF4
  「依赖必须先发布、禁止同一 PR 捎带适配依赖」，配方在 `build()` 内用
  cmake + Ninja 内嵌编译上游 `poppler-25.12.0/qt5/src/*.cc` 为静态库
  `libpoppler-qt5.a`，直接链入 `pdf` 插件，**不安装**进 package。
- **Qt5 依赖选择**：`qt5-qtbase/5.15.2.2`（5.15.2 为 `-no-widgets` 构建，
  qpdfview 需要 `QT += widgets`）；`qt5-qtsvg/5.15.2`（全部图标为 SVG），
  其 `.pri` 精确要求 `qt5-qtbase/5.15.2` → `override` 统一到 5.15.2.2。
- **qmake 模块发现**：`qt5-qtsvg` 的 `mkspecs/modules/*.pri` 记录构建期绝对
  路径（`.conan2/p/b/...`），需复制到 build 目录、正则改写为 package 目录，
  再经 `QMAKEMODULES` 暴露给 qmake。
- **代码签名**：OHOS 上 ELF 必须带有效 `.codesign` 段才能 `exec`/`dlopen`，
  而 strip 会破坏签名 → `QMAKE_STRIP=` 置空，并在 `package()` 末尾对
  `bin/` 下 ELF 执行 `binary-sign-tool sign -selfSign 1`。
- **运行期环境**：`package_info()` 注入 `LD_LIBRARY_PATH`、`QT_PLUGIN_PATH`
  （qtsvg 的 iconengines/imageformats）与 `FONTCONFIG_PATH`（conan fontconfig）。

### 已知问题 / 与 Linux 的差异

- **无 UI 翻译**：`translations/*.ts` 需 `lrelease`，制品仓 `qt5-qttools` 缺位
  （仅有 Qt6 的 `qttools`）、系统亦无 `lrelease` → 无可执行 `.qm`，按上游默认
  处理（不存在即不装）。
- **无 PS / DjVu 后端**：`libspectre`、`djvulibre` 不在制品仓，
  `CONFIG+=without_ps without_djvu`。
- **无 PDF 打印**：无 Qt5PrintSupport 的 cups 插件，`CONFIG+=without_cups`。
- **QSettings 回退**：`qt5-qtbase/5.15.2.2` 未构建 Qt5Sql，`CONFIG+=without_sql`。
- **`-lz` 走系统 zlib**：OHOS NDK sysroot 的 `libz.so` 无 SONAME，链接后
  `DT_NEEDED` 为 `libz.so`，与 `libQt5Core.so` 自身一致；conan `zlib/1.3.1.1`
  仅作依赖图一致性 override，不参与链接路径。

## 依赖关系

| 类型 | 依赖 | 说明 |
|------|------|------|
| 编译/运行 | `qt5-qtbase/5.15.2.2` | Qt5 Core/Gui/Widgets/Xml/Network（moc/uic/rcc/qmake） |
| 编译/运行 | `qt5-qtsvg/5.15.2` | SVG 图标（图标引擎/图像格式插件） |
| 编译/运行 | `poppler/25.12.0.2` | PDF 渲染后端（`libpoppler.so.155`） |
| 编译 | `fontconfig/2.18.1.1` | 字体配置 |
| 编译 | `expat/2.8.2.1`、`zlib/1.3.1.1` | 依赖图版本一致性 override |
| 内嵌 | poppler `qt5/src/*.cc` | 静态库 `libpoppler-qt5.a`，不安装进 package |

## 参考资料

- 官网 / 源码：<https://launchpad.net/qpdfview>
- 图标 / 桌面集成依赖：Qt5 SVG
- 适配笔记：`0.5.0/notes.md`；构建配方：`0.5.0/conanfile.py`
