# khelpcenter 26.04.0 — 适配笔记（HarmonyOS PC / aarch64）

## 软件背景

khelpcenter 是 KDE 帮助中心（KDE Gear 26.04，KF6/Qt6/CMake）。上游形态：
- `khelpcenter` GUI 可执行程序：Qt **WebEngineWidgets** 帮助渲染视图
  （view.cpp/mainwindow.cpp/printdoc.cpp/pagesearchbar.cpp 等），另依赖
  Qt PrintSupport、ktexttemplate(Grantlee)、kio、kxmlgui 等一大串 KF6 框架
- `searchhandlers/`：headless Xapian 全文检索栈（khc_xapianindexer /
  khc_xapiansearch）
- `docmetainfo/docentry/docentrytraverser`：文档元数据模型
- `tests/testmetainfo`：上游测试（唯一一个）
- `doc/`：kdoctools handbook（docbook）

## OHOS 适配决策（W0 依赖预检结论）

上游 REQUIRED 依赖中有两个在 ohpcd 制品仓不可用：
1. **Qt6::WebEngineWidgets**：qtwebengine 无任何版本发布；且 qtbase/6.11.1
   不含 Qt6::PrintSupport（algobox 1.1.1 配方 notes 已证实同坑）→ GUI 帮助
   浏览器整体不可构建。渲染主程序（含 grantleeformatter/ktexttemplate 链、
   kio/kxmlgui/kbookmarks/kwindowsystem 等 GUI 框架依赖）全部裁出。
2. 其余 KF6 GUI 框架件（kio/kxmlgui/kbookmarks/kcompletion/kdbusaddons/
   ktexttemplate/kwidgetsaddons/kwindowsystem）仅被裁掉的 GUI 使用。

**交付形态**（audiocd 26.04.3 裁 KIO worker 同款先例）：
- `libkhcdocmetainfo.so`：DocEntry/DocMetaInfo/DocEntryTraverser + kcfg 生成
  的 Prefs 配置类——文档元数据模型库，可被嵌入应用与上游测试消费
- `libexec/khc_xapianindexer`：扫描 KDocTools::documentationDirs()，把
  *.cache.bz2 文档缓存（CacheReader/KCompressionDevice + libxml2
  htmlTextDump）灌进 Xapian 全文索引
- `libexec/khc_xapiansearch`：查询 Xapian 索引，按 searchhandler 协议输出
  HTML 片段
- 数据文件：plugins/*.desktop、templates/*.html、glossary/toc xslt

## 依赖版本线（graph 冲突消解）

- qtbase/6.11.1（Qt Core/Gui/Widgets/Xml）
- karchive/6.19.0 —— 对齐 kdoctools/6.19.0 的钉定（kdoctools 闭包：
  karchive/6.19.0 + zlib/1.3.1.1 + libxml2/2.15.3 + libxslt/1.1.45.1）
- kconfig/6.26.0 + kcoreaddons/6.26.0 + ki18n/6.26.0（6.26 线，闭包干净）
- kdoctools/6.19.0（本任务的关键解锁依赖，已发布）
- xapian-core/1.4.26（binary 可用实测：OHOS aarch64 package
  4178e02c63d7574e37468da4e7276fa15c76c47c）
- libxml2/2.15.3
- ecm/6.26.0（build tool）
- zlib/1.3.1.1 override=True（kdoctools/xapian 共同钉定，libkdegames
  26.04.0 override 先例；kconfigwidgets 6.18 线曾引 kconfig/6.18.0 冲突，
  裁掉后统一）

## 构建要点

- `KF_IGNORE_PLATFORM_CHECK=TRUE`（OHOS 不在 KDE 平台表，audiocd 先例）
- `KF_SKIP_PO_PROCESSING=ON`（CI worker msgfmt 无法加载自身 libintl，
  alkimia 8.2.1 先例；本地同样跳过翻译目录）
- `BUILD_TESTING=ON`：上游 tests/testmetainfo 纳入构建（链接 khcdocmetainfo
  库而非重新编源文件）
- ECM_MODULE_PATH 手工注入（CMakeDeps 生成的 ECMConfig.cmake 不传导该变量）
- conan_cmakedeps_paths.cmake 手工生成（qtbase/KF6 系 cmake_find_mode=none，
  audiocd/libkcddb 先例）；传递依赖 zlib/zstd/libxslt 的 cmake 目录也注入
  （karchive 的 KF6ArchiveConfig.cmake find_package(ZLIB) 需要）
- xapian-core 包自带 lib/cmake/xapian/xapian-config.cmake（XAPIAN_LIBRARIES/
  XAPIAN_INCLUDE_DIR 变量风格，prefix 在打包时烤死为 "/"）——generate() 时
  重写 prefix 到 conan 包目录并去 CACHE 声明，find_package(Xapian) 模块态
  解析通过
- 链接旗标 `-Wl,-z,max-page-size=0x1000`（shared/module/exe 三通道）：
  lld 默认 0x10000 页大小会把 .dynsym/.dynstr 放进分离高址 RW LOAD 段，
  OHOS musl 加载器拒绝 mmap（"Permission denied"），audiocd 先例
- DocMetaInfo/DocEntry/DocEntryTraverser 类无导出宏（上游是可执行程序内部
  类）→ 库目标设 CXX_VISIBILITY_PRESET "default" 保符号可见
- 构建环境 LD_LIBRARY_PATH：依赖包 lib 目录 + /system/lib64（kconfig_compiler
  /meinproc6/moc 等 host 工具是 OHOS 二进制，需要兼容 libc++_shared，
  audiocd 先例）

## 上游测试（N 口径与真跑）

上游测试套件：`tests/testmetainfo`（1 个测试目标，ecm_mark_as_test；无
autotests/）。上游无 ctest 注册（原 tests/CMakeLists.txt 无 add_test 行，
由 ECMAddTests 宏负责——本适配显式 add_test 注册并真跑）。语义：遍历
DocMetaInfo 元数据树（traverser 协议）。适配后在 conan create 的
test_package 阶段同步验证库消费面（Prefs 配置单例 + DocEntry 属性往返 +
DocMetaInfo traverse 协议运行）。

## 已知限制

- GUI 帮助浏览器（WebEngine 渲染、打印、书签、字体缩放）不在本平台交付面
- doc/ docbook handbook 构建裁出（kdoctools_create_handbook 需要 docbook
  定制数据，OHOS help bundle 不发布）；KDocTools::documentationDirs() API
  本身仍可用（kdoctools 6.19.0 依赖包）
- man.desktop 的 khc_mansearch.py 保留安装（searchhandler 协议数据文件）
