# qpdfview 0.5.0 适配笔记

> **状态：✅ 本地闭环完成（W3 全量 `conan create` + `test_package` 20 断言全部通过）**
> 已完成：W0 依赖发布检查、R47 语言预检、上游源码核验、依赖图全量解析、
> 内嵌 poppler-qt5 绑定验证、qmake 构建验证、`conan create` 闭环、
> `ohc-run.py finish` 收尾（conan-verify G1–G3 通过 + W3 本地 CI 模拟：
> setup.sh + build_and_test.sh，L0 质量门全过，通过率 100%）。

## 软件身份

- **软件名**: qpdfview 0.5.0（Adam Reichold / qpdfview 项目）
- **上游仓库**: https://launchpad.net/qpdfview（Launchpad 托管，bzr 仓库）
- **类型**: Qt5 GUI 标签页式文档查看器（PDF / PS / DjVu / 图像），非库
- **许可证**: GPL-2.0-or-later（`COPYING` = GPL-2 全文）
- **源码规模**: `sources/` 约 70 个 .cpp/.h，`synctex/` 捆绑上游源码，
  `translations/` 57 个 `.ts`，`icons/` + `help/` 各带 `.qrc`

## 编译环境

- 构建系统: **qmake**（顶层 `qpdfview.pro`，`TEMPLATE = subdirs` + `CONFIG += ordered`）
  - 子工程：`application.pro`（主程序）+ `pdf-plugin.pro` / `ps-plugin.pro` /
    `djvu-plugin.pro` / `image-plugin.pro`（各自独立链接的插件）
- 编译器: clang 15 / clang++（OHOS aarch64，qmake 自动选 `mkspecs/linux-clang`）
- Profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS / 6.0 / armv8 / clang 15 /
  libc++ / cppstd 17 / Release）
- Conan: 2.29.1（OHOS 适配版），remote = `ohpcd`
- 并发: `make -j1`（本环境 `make -j` 的 jobserver mkfifo 报
  `Operation not permitted`，只能用 -j1/-j2）

## 源码核验

| 项 | 值 | 证据 |
|---|---|---|
| 官方下载 URL | `https://launchpad.net/qpdfview/trunk/0.5.0/+download/qpdfview-0.5.tar.gz` | Launchpad 0.5.0 发布页 |
| SHA256 | `44efc440a461cbdd757a9b396f1461ee7a2f4364e81df55bd0221f910219be99` | `sha256sum` 实测 |
| 归档顶层 | `qpdfview-0.5/{sources,synctex,translations,icons,help,miscellaneous,qpdfview.pro,...}` | `tar tzf` |
| 版本号 | `APPLICATION_VERSION = 0.5.0`（`qpdfview.pri`） | grep |
| R47 语言预检 | task=cpp / detected=cpp | `ohc-run.py lang-preflight` |

> **R39 源码来源**：使用 Launchpad 官方发布页 tarball，**未**使用 Debian 的
> `qpdfview_0.5.0+ds.orig.tar.gz`（`+ds` 为 Debian 重打包，PF7 明确拒绝）。

## 依赖（W0 检查全部已发布）

| 依赖 | 版本 | 说明 |
|------|------|------|
| qt5-qtbase | 5.15.2.2 | qmake 5.15.2；5.15.2 为 `-no-widgets` 构建，qpdfview 声明 `QT += widgets` → 用 5.15.2.2（baka 先例同解） |
| qt5-qtsvg | 5.15.2 | qpdfview 全部图标都是 SVG；`WITH_SVG` 只 gate `icons.qrc` + `QT += svg`，关掉则工具栏图标全空 |
| poppler | 25.12.0.2 | PDF 渲染后端（`ENABLE_QT5=OFF`，只装 C++/glib API） |
| fontconfig | 2.18.1.1 | 依赖图版本冲突 override（cairo 声明 2.18.1） |
| zlib | 1.3.1.1 | 依赖图版本冲突 override（**仅图一致性**，见下「zlib / -lz」） |
| expat | 2.8.2.1 | 依赖图版本冲突 override（fontconfig 声明精确 2.8.2.1） |

### 为什么不另起 poppler-qt5 PR

W0 依赖发布检查（`conan download -r=ohpcd --only-recipe`）结论：

- `poppler*` 在制品仓只有 25.12.0 / 25.12.0.1 / 25.12.0.2，且 recipe 里
  `ENABLE_QT5=OFF`、只安装 C++/glib API；
- **没有**独立的 `poppler-qt5` 配方，registry / 文件系统 / git 历史三处皆无。

而 W0/PF4 规定「依赖必须先发布」，且**禁止在同一个 PR 捎带适配依赖**。
因此本配方在 `build()` 内**内嵌编译**上游 poppler 自带的 Qt5 绑定
（`poppler-25.12.0/qt5/src/` 共 17 个 .cc），编成**静态库**
`libpoppler-qt5.a` 直接链入 pdf 插件，**不安装**进 package —— 运行时只依赖
制品仓的 `libpoppler.so.155`，不与 `libpoppler-cpp.so` 的公开 API 发生歧义
（poppler 仓库里 qt5 绑定与 cpp 绑定本就是两套独立符号）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | registry 无 poppler-qt5 制品 | 上游 poppler 的 Qt5 绑定从未单独发布 | 内嵌编译上游 `qt5/src/*.cc` 为静态库，链入 pdf 插件（见上） |
| 2 | `qt5-qtsvg/5.15.2` 声明精确 `qt5-qtbase/5.15.2`，与本配方 5.15.2.2 冲突 | Conan 精确版本约束 | `override=True` 统一到 5.15.2.2（补丁版本 API 兼容；实测两者预编译包 id 一致，qtsvg 二进制无需重建） |
| 3 | qmake 报 `Project ERROR: Unknown module(s) in QT: ... svg` | qt5-qtsvg 包内 `mkspecs/modules/qt_lib_svg.pri` 记录的是**构建时**绝对路径（`.../.conan2/p/b/qt5-qXXXX/b`），随 conan 清理消失 | `_setup_qmake_modules()`：复制 `.pri` 到 build 目录、正则改写为 package 目录，经 `QMAKEMODULES` 暴露（baka 先例同解） |
| 4 | qmake 报 `Project ERROR: Cannot run target compiler 'clang++'` | qmake 探测目标编译器时用**裸名字**走 PATH 查找，PATH 不含工具链目录即失败（同类 PATH 缺失：E540） | `build_env.prepend_path("PATH", <clang 目录>)` |
| 5 | `poppler-form.h` 无条件使用 `std::optional` | poppler 25.12 头文件要求 C++17 | qmake 命令行 `CONFIG+=c++17` 强制（上游默认 `CONFIG += c++11` 不够） |
| 6 | 链接期 `cannot find -lQt5Svg` / 运行期 `Error loading shared library libQt5Svg.so.5` | 多前缀 conan Qt 安装，Qt5Svg 所在 lib 目录不是可执行文件自己的目录 | qmake 命令行 `QMAKE_RPATHDIR+=<libdir>` 显式补进 RUNPATH（实测有效，会 prepend 到 LFLAGS） |
| 7 | `pkg-config --exists synctex` 命中 poppler 自带的 synctex.pc，链接找不到 `synctex_scanner_*` | poppler 源码树里带一份 synctex.pc | `PKG_CONFIG_LIBDIR` 只指向配方生成的 vendor 目录 → 探测恒为假，走「上游捆绑源码 + 系统 zlib」分支 |
| 8 | 内嵌 cmake 子工程与 qpdfview 本体互相干扰 | `pdf-plugin.pro` 的 synctex 探测对构建目录里的 Qt5Core 头敏感 | cmake 子工程隔离到 `build/poppler-qt5-vendor/`，独立 `config.h` 占位 |
| 9 | `config.h` 缺失（上游 qt5 绑定 `#include "config.h"`，而 poppler 只装 `poppler/poppler-config.h`） | poppler 的 `config.h.cmake` 默认指向已不再安装的 `config.h/cmake-config.h` | 生成单行转发 `#include <poppler/poppler-config.h>`。依据：`poppler-config.h` 自带说明「We duplicate some of the config.h #define's here since they are used in some of the header files we install」；逐条核查 `qt5/src` 引用的 `config.h.cmake` 宏（`ENABLE_NSS3`/`ENABLE_GPGME`/`ENABLE_SIGNATURES`/`USE_CMS`/`VERSION`，全部关闭或已覆盖）与安装头里唯一未公开的 `ENABLE_ZLIB_UNCOMPRESS`（`Stream.h`，上游该选项关闭），确认单行转发即足够 |
| 10 | OHOS 加载器拒绝 stripped ELF | 内核要求 ELF 带有效 `.codesign` 段；`llvm-strip` 等改写 ELF 后签名失效，加载即被拒（知识图谱 E077 / E045） | qmake 命令行 `QMAKE_STRIP=` 置空，移除 strip 规则 |
| 11 | 产物无法 exec / dlopen | HarmonyOS 要求 ELF 代码签名 | `package()` 最后一步对 `bin/` 下 3 个 ELF 做 `binary-sign-tool sign -selfSign 1`（adwaita-qt/1.4.2 同法） |
| 12 | 运行期 `Fontconfig error: Cannot load default config file` | conan fontconfig 包把 `fonts.conf` 装在 `<pkg>/etc/fonts` | `package_info()` 注入 `FONTCONFIG_PATH` |
| 13 | 运行期 SVG 图标不显示 | OHOS 无系统级 Qt 插件目录，qtsvg 的 `iconengines`/`imageformats` 插件找不到 | `package_info()` 注入 `QT_PLUGIN_PATH` |
| 14 | `make -j` 报 `jobserver mkfifo: Operation not permitted` | 本环境限制 | `make -j1` |
| 15 | 远端 CI `test_package` 最后一条断言失败：`[fail] rendered page contains non-white pixels (text actually drawn)`，stderr 有 `Error: Couldn't find a font for 'Helvetica'` | CI worker 的 fontconfig 没有任何可用字体目录（`FONTCONFIG_PATH` 指向的 conan fontconfig 里 `<dir>` 均不存在），poppler 无法光栅化 Type1 字形 → 整页空白；文字抽取/检索仍通过（不依赖字体文件） | `test_package/test.pdf` 改用**自包含 Type3 字体**（字形 = 矢量填充矩形），渲染断言不再依赖系统字体 |

## zlib / -lz 说明

`application.pro` 的 synctex 分支有 `LIBS += -lz`。本配方**故意不**把
conan 的 `zlib` 加进 `LIBRARY_PATH`：

- OHOS NDK sysroot 提供 `libz.so`（**无 SONAME**），链接后 DT_NEEDED 只写
  `libz.so`，与 `libQt5Core.so` 自身的 DT_NEEDED 完全一致，运行期由系统
  加载器直接解析；
- 若改用制品仓 `zlib` 的 `libz.so.1`，会把每个 DT_NEEDED 污染成
  `libz.so.1`，与系统库不一致。

因此 `zlib/1.3.1.1` 在 `requirements()` 里**仅作依赖图一致性 override**，
不参与链接路径。

## 禁用的上游子工程

| 子工程 | 开关 | 原因 |
|--------|------|------|
| ps-plugin | `CONFIG+=without_ps` | libspectre 不在制品仓 |
| djvu-plugin | `CONFIG+=without_djvu` | djvulibre 不在制品仓 |
| sql（QSettings） | `CONFIG+=without_sql` | qt5-qtbase/5.15.2.2 未构建 Qt5Sql（`libQt5Sql.so` 不存在），QSettings 回退 |
| cups（打印） | `CONFIG+=without_cups` | 同版本无 Qt5PrintSupport 的 cups 插件，PDF 打印不可用 |
| fitz-plugin | — | 上游 `with_fitz` 默认即关闭 |

## UI 翻译

`translations/` 下 57 个 `.ts` 需要 `lrelease` 编译成 `.qm`。制品仓
`qt5-qttools*` 零匹配（只有 Qt6 的 `qttools`），系统也没有 `lrelease`
（`find / -name "lrelease*"` 为空）→ **无可执行 .qm**，按上游默认
（不存在即不装）处理。这是本适配唯一的功能性缺失，已在 PR 正文中如实说明。

## 关键适配点（conanfile.py）

- `source()`：`get()` 主源码（Launchpad 官方 tarball）+ poppler 源码到
  `poppler-source/`（只取 `qt5/src/*` 与少量私有头）
- `build()`：
  1. `_build_vendor_poppler_qt5()` —— cmake + Ninja 内嵌编译静态库
     `libpoppler-qt5.a`（C++23 + `-fexperimental-library` + `-fPIC` +
     `CMAKE_AUTOMOC` + `generate_export_header` + `configure_file(poppler-version.h.in)`）
  2. `_write_poppler_qt5_pc()` —— 生成无 `Requires` 的 `poppler-qt5.pc`
  3. `_setup_qmake_modules()` —— 修复 qt5-qtsvg 的 `.pri` 路径
  4. qmake 命令行：`CONFIG+=without_ps without_djvu without_sql without_cups c++17`、
     `QMAKE_STRIP=`、`QMAKE_CC/CXX/LINK/LINK_SHLIB`（R33：来自 conf，不裸用
     `${CC}`）、各依赖 `QMAKE_RPATHDIR+=`、安装路径变量（由
     `self.package_folder` 烘焙）
  5. `make -j1 QMAKE_STRIP=""`
- `package()`：`make install`（44 个文件直接进 package）→ `_sign_elfs()`
  对 `bin/` 下 3 个 ELF 签章
- `package_info()`：`cpp_info.bindirs = ["bin"]`；对每个依赖 prepend
  `LD_LIBRARY_PATH`；`qt5-*` 额外 prepend `PATH` 与 `QT_PLUGIN_PATH`；
  fontconfig 段 prepend `FONTCONFIG_PATH`

## 上游测试情况（R51 三步法）

1. **清点**：上游源码包内**无 `tests/` 目录**、无 `ctest`/`pytest` 配置、
   无 `make check` 目标（`qpdfview.pro` 只有 `TEMPLATE = subdirs` +
   `TRANSLATIONS`）。57 个 `.ts` 是翻译源，不是测试。
2. **实测**：无可执行上游测试。
3. **自行补充**（R34 + R51）：`test_package/` 共 **20 条断言**：
   - 包内容完整性 6 条（`bin/qpdfview`、`bin/libqpdfview_pdf.so`、
     `bin/libqpdfview_image.so`、`share/applications/qpdfview.desktop`、
     `share/man/man1/qpdfview.1`、`share/icons/.../qpdfview.svg`）
   - `qpdfview --help` 冒烟 1 条（R40：GUI 应用必须真实 exec）
   - 插件端到端 13 条：dlopen `libqpdfview_pdf.so` → `instance()` →
     IID == `local.qpdfview.Plugin` → `qobject_cast<qpdfview::Plugin*>` →
     `loadDocument()` → `numberOfPages() == 1` → `page(0)` → 页面尺寸
     300x120 pt（来自 MediaBox）→ `text()` 抽出 `Hello HarmonyOS` →
     `search("HarmonyOS")` 命中 → `render(144dpi)` 得 600x240 px QImage →
     渲染结果含非白像素（文字真的画上去了）

   测试资产 `test_package/test.pdf`（1259 B，ASCII，1 页，MediaBox
   `[0 0 300 120]`，文本 `Hello HarmonyOS!`）。**该 PDF 自带 Type3 字体**：
   每个字形的 charproc 用矢量填充矩形绘制，因此渲染不依赖宿主机
   fontconfig 能找到系统字体；文本抽取/检索仍通过 `/Encoding
   /Differences` 的字形名映射工作。详见「渲染断言与 CI 字体」一节。

## 渲染断言与 CI 字体

插件端到端测试的最后一条断言要求渲染出的 QImage 含非白像素。原先
`test.pdf` 的内容是 `/BaseFont /Helvetica` 文本，命中该断言依赖运行环境
的 fontconfig 能解析出 Helvetica（poppler 找不到字体时只打印
`Couldn't find a font for 'Helvetica'` 并画出空白页，**不会**报致命错误）。
本机 `/system/fonts` 有字体所以本地全绿，但 CI worker 无字体目录 → 同一
份代码在 CI 上渲染为空 → 断言失败。

修复：`test.pdf` 改为**自包含 Type3 字体**——13 个字形经 charproc 绘制
（非空格字形复用同一个矢量填充矩形 charproc，空格 charproc 无可见轮廓，
但 `d1` 仍声明 300/1000 的前进宽度），`/Encoding /Differences` 仍给出
真实字形名（`/H /e /l ... /exclam`）。这样：

- `text()` / `search()` 断言不变（Type3 的字形名照样映射到 Unicode）；
- `render(144dpi)` 仍是 600x240；
- 「非白像素」由 poppler 真正执行 Type3 charproc 光栅化得到，
  与宿主机是否安装字体无关，也不再出现 `Couldn't find a font` 警告。

## 判定

- **status**: `built`（W3 本地 CI 模拟通过，L0 质量门全过、`test_package` 20 断言 100%；
  R46 生命周期 `result.json` 未触发自动升级，故按终态 `built` 归档）
---

**编译结束**: 2026-09-29 15:04
**最终状态**: built
