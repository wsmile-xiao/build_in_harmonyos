# vprerex 6.5.1 适配笔记

## 编译环境
- 构建系统: cmake（自研 CMakeLists 替换上游 qmake 工程 vprerex.pro）
- 编译日期: 2026-09-24
- 编译器: clang 15 / clang++（OHOS aarch64-musl，profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built

## 上游信息与测试入口核验（R51）
- 上游: CTAN prerex 宏包 <http://www.ctan.org/tex-archive/graphics/prerex>；
  vprerex 6.5.1 的源码是包内 `doc/vprerex-6.5.1.tar.gz`
  （官方镜像直链 <https://mirrors.ctan.org/graphics/prerex/doc/vprerex-6.5.1.tar.gz>，
  sha256 `fef226574a214d39d4f09017b29167b4efc24bc9f592d69f56127d7e0d33245b`，19127 字节）。
- 源码包共 14 个文件（`ChangeLog/COPYING/INSTALL/README/vprerex.{1,desktop,png,pro}`
  + `main.cpp/window.{h,cpp}/documentwidget.{h,cpp}` + `window.ui`）。
- **上游测试入口清点**：无 `tests/` 目录、无 CTest/`meson test` 注册、无 `make check`
  目标、无 `*.pro` 中的 `test` target；`vprerex.pro` 是唯一构建描述且只做编译链接。
  → 上游无自动化测试可执行（证据见 `test_package/MANIFEST.yml`）。
- 依赖（`vprerex.pro` / INSTALL）：Qt5 Widgets + `libpoppler-qt5`；运行时调用
  `xterm` 与 `prerex`（独立组件，非本包依赖）。

## 编译步骤（真实命令）
```bash
# 1) 源码获取（init-build）
python3 scripts/ohc-run.py init-build vprerex 6.5.1 \
    --url=https://mirrors.ctan.org/graphics/prerex/doc/vprerex-6.5.1.tar.gz
# 2) 语言预检（R47）
python3 scripts/ohc-run.py lang-preflight vprerex 6.5.1 \
    --src /storage/Users/currentUser/tmp/builds/vprerex-6.5.1.work   # → cpp 匹配
# 3) 真实构建 + 打包 + test_package
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    -s build_type=Release
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 制品仓 poppler 全版本 `ENABLE_QT5=OFF`，无 `poppler-qt5` 包 → 上游 `-lpoppler-qt5` 无法满足 | poppler 配方把 Qt 绑定固定关闭（Qt 绑定会耦合特定 Qt 大版本）；registry 无独立 poppler-qt5 包 | 不改上游源码：新增 **poppler-qt5 兼容 shim**（`poppler-qt5.h/.cpp`），在 poppler 包自带的 **core** 库上重实现 vprerex 用到的 `Poppler::Document/Page/Link/LinkBrowse` 子集（E324 的 core 变体） |
| 2 | upstream qmake 工程硬编码 `/usr/include/poppler/qt5`、`/usr/include/qt5`、`-L/usr/lib64` | qmake 工程不适配交叉编译 | 自研 CMakeLists；`window.ui` 用 `uic`、`Q_OBJECT` 头用 `moc`（qt5-qtbase/bin），运行 moc/uic 时 `LD_LIBRARY_PATH` 指向 qt5 lib |
| 3 | `poppler-config.h file not found`、`std::span/std::optional/std::is_base_of_v not found` | core 头 `goo/gfile.h` 以引号包含同目录 `poppler-config.h`；core 头要求 C++20+（`std::span`/concepts），poppler 自身按 C++23 构建 | 编译 shim 时同时给 `-I<poppler>/include` 与 `-I<poppler>/include/poppler`；shim 单独成静态库并以 `CXX_STANDARD 23` 编译 |
| 4 | zlib "Version conflict" | `qt5-qtbase/5.15.2.2` 链 `zlib/1.3.1`，`poppler/25.12.0.1` 链 `zlib/1.3.1.1` | consumer 侧 `self.requires("zlib/1.3.1.1", override=True)` 统一 |
| 5 | 无法在无显示环境验证 GUI 程序 | OHOS worker 无图形会话，程序默认进入 GUI 事件循环 | main.cpp 增加无 GUI 入口 `--version` / `--help` / `--check-pdf <pdf>`（后者经 shim 加载 PDF、渲染每页并提取链接），供 test_package 做 headless 验证；另加 `--check-gui <pdf>`（**真实 GUI 路径**：QApplication + offscreen QPA + 真实 MainWindow/DocumentWidget + 真实渲染 grab），见补丁 0005 |
| 6 | `get() got an unexpected keyword argument 'tar_format'` | `conan.tools.files.get()` 不接受 `tar_format` kwarg（conandata 的 spec 又要求该字段） | `source()` 显式取 `url`/`sha256` 调 `get()` |

## 源码修改（补丁清单）
- `0001-CMakeLists.txt.patch` — 新增 `CMakeLists.txt`（替换上游 qmake 工程；
  Qt5 手动接线、uic/moc 显式调用、shim 以 C++23 单独成静态库、安装 bin/man/desktop/icon）。
- `0002-main.cpp.patch` — `main.cpp` 增加无 GUI 入口
  （`--version` / `--help` / `--check-pdf <pdf>`，在 **QApplication 之前**处理，
  因此不需要显示环境、也不需要 Qt 平台插件；banner 抽成 `printBanner()`），
  仅新增代码，原有 GUI 行为不变。
- `0003-poppler-qt5.cpp.patch` — 新增 `poppler-qt5.cpp`（poppler-qt5 → poppler core API
  实现：`Document::load`→`PDFDoc`、`Page::renderToImage`→`SplashOutputDev(splashModeXBGR8)` +
  `PDFDoc::displayPageSlice`、`Page::links()`→`PDFDoc::getLinks()` +
  `AnnotLink::getRect()`/`LinkURI::getURI()`）。
- `0004-poppler-qt5.h.patch` — 新增 `poppler-qt5.h`（声明 vprerex 实际用到的
  `Poppler::Document/Page/Link/LinkBrowse` 子集）。
- `0005-main.cpp.patch` — `main.cpp` 增加**真实 GUI 路径**自测入口 `--check-gui <pdf>`
  （在 `QApplication` 之后处理）：构造真实 `QApplication`（offscreen QPA 平台插件）、
  真实 `Window`（ui_window.h）与 `DocumentWidget`，经 shim 加载 PDF、跑 Qt 事件循环并
  `QWidget::grab()` 真实渲染整棵控件树，输出页数/grab 尺寸/非白像素数供测试断言；
  仅新增代码，原有 GUI 行为不变。

> 上游 `main.cpp/window.*/documentwidget.*/window.ui` 的既有逻辑零修改。

## 对话与决策记录

### 对话 #1 — 源与目标确认（2026-09-24）
- 用户给定 `vprerex 6.5.1` + CTAN prerex 包地址。CTAN `graphics/prerex/` 只列
  `prerex.sty/README/chart.*`，逐一排查后确认 vprerex 源码是该包内的
  `doc/vprerex-6.5.1.tar.gz`（官方镜像直链可下载，sha256 与包内一致）。

### 对话 #2 — W0 依赖核验（2026-09-24）
- `conan download qt5-qtbase/5.15.2.2 --only-recipe` → 可消费。
- `conan list poppler/* -r=ohpcd` → 25.12.0/25.12.0.1/25.12.0.2 三条，**全部**
  以 `ENABLE_QT5=OFF` 发布；无 `poppler-qt5/*` recipe。→ 上游 `-lpoppler-qt5`
  在制品仓无对应包。
- 决策：不改上游源码，改走"自建兼容 shim"路线；因 vprerex 需要**链接注记**
  （poppler-cpp 无 link API），shim 后端选用 poppler 包同时发布的 **core**
  头/库（`libpoppler.so` + `include/poppler`）。

### 对话 #3 — 可行性验证（2026-09-24）
- 用 `nm -D` 确认 core 必需符号（`Page::getLinks`、`PDFDoc::getLinks`、
  `AnnotLink::getRect`、`LinkURI::getURI`、`SplashOutputDev`）均已导出。
- 独立最小驱动实测 shim：`pages=1 / image=200x200 / link=coord: 3,4`；
  逐像素旁证 `pixel(100,100)=#ff1818`（红对角线）、`pixel(3,3)=#ffffff`（纸面）
  → 渲染字节序与链接归一化均正确。

### 对话 #4 — 收尾与门禁（2026-09-24）
- `conan create` / `conan-verify`（G0-G4+L2/L4/L5）/ W3 本地 CI（L0/L1 含 L1e）全部通过。
- 本地 `origin` 指向滞后 fork（落后 3235 提交），W2/JC 的 `origin/main...HEAD`
  基线失真；已将本地 `refs/remotes/origin/main` 对齐真实基线 `upstream/main`，
  并用等价 CI 的 `pr.diff`（15 文件 / 单软件）跑通 JC 原子性检查。

## 依赖版本
- `qt5-qtbase/5.15.2.2`（Core/Gui/Widgets）
- `poppler/25.12.0.1`（core 库 `libpoppler.so.155` + `include/poppler`）
- `zlib/1.3.1.1`（override 统一；传递依赖：freetype/2.14.3、dbus/1.14.10、expat/2.8.2）

## 验证结果

```bash
# 真实 conan create（含 test_package）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -s build_type=Release
# → Build/Test 均通过，package bin/vprerex 带 .codesign 段（已自签）

# test_package（OHOS headless）
[1/3] vprerex --version   → "This is vprerex, version 6.5.1."  exit 0
[2/3] vprerex --help      → "Usage: vprerex ..."               exit 0
[3/3] vprerex --check-pdf selftest.pdf
      vprerex-check: page=1 image=200x200
      vprerex-check: page=1 link=coord: 3,4
      vprerex-check: ok pages=1 links=1
      → OK: vprerex headless smoke + poppler-qt5 shim functional check passed

# test_package（OHOS 真实 GUI 路径测试，test_gui_ohos.sh）
$ QT_QPA_PLATFORM=offscreen vprerex --check-gui selftest.pdf
      vprerex-gui: pages=1
      vprerex-gui: grab=960x1000
      vprerex-gui: pixels=960000 nonwhite=867076 rgbsum=691536239
      vprerex-gui: ok pages=1 grab=960x1000 nonwhite=867076
      → OK: vprerex real GUI path (QApplication offscreen QPA + MainWindow +
             DocumentWidget + poppler-qt5 shim + render) passed on OHOS
```

渲染正确性旁证（shim 独立小驱动，验证像素语义）：
`pixel(100,100)=#ff1818`（图表对角线红）、`pixel(3,3)=#ffffff`（纸面白），
链接矩形归一化 `(0.05, 0.80, 0.45x0.15)` 与 PDF `Rect [10 10 100 40]` / 200x200 页一致。

## 注意事项
- `--check-pdf` 是 OHOS 适配新增的无 GUI 验证入口，正常运行路径不经过它。
- `--check-gui` 是 OHOS 适配新增的**真实 GUI 路径**自测入口（补丁 0005）：它真的构造
  `QApplication`（因此会加载 qt5-qtbase 的 `plugins/platforms/libqoffscreen.so` 平台插件）、
  真实 `MainWindow` 与 `DocumentWidget`，并 `grab()` 真实渲染结果；正常运行路径同样不经过它。
  test_package 的两个脚本分别覆盖「shim 功能」与「真实 GUI 栈」。
- 制品仓 poppler 无 Qt 绑定时，同类消费方（需 poppler-qt5 的 PDF GUI）可复用本 shim，
  但 API 面按 vprerex 实际调用裁剪（Document/Page/Link/LinkBrowse）。
---

**编译结束**: 2026-09-24 23:39
**最终状态**: built
