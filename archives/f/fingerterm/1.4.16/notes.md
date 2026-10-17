# fingerterm 1.4.16 适配笔记（HarmonyOS PC / arm64）

## 软件概览

fingerterm 是 Sailfish OS 出品的 Qt Quick 终端模拟器（GPL-2.0）：C++ 实现
VT 解析引擎（terminal.cpp，1533 行）+ QQuickPaintedItem 渲染器（textrender.cpp）
+ pty 层（ptyiface.cpp，forkpty）+ QML 虚拟键盘/UI（qml/*.qml）。上游 1.4.16
为 qmake 工程（fingerterm.pro），依赖 Qt5（core gui qml quick）。

- 上游：https://github.com/sailfishos/fingerterm （tag 1.4.16 = 9b163d49）
- 源码 sha256：`3dc651ff449c8a7f26af2a9e1fa30fa869fffa805f26ec8619bf553d1a69ee2e`

## 适配决策（W0/W0b 核验）

1. **依赖链已发布**（conan download --only-recipe 实测）：qtbase/6.11.1 ✅、
   qtdeclarative/6.11.1 ✅、qtshadertools/6.11.1 ✅ —— 独立可做，无需先发依赖。
2. **上游无 url 字段**，按任务背景核定为 sailfishos 官方仓（KDE fork 不存在，
   GitHub API 确认 sailfishos/fingerterm 为权威源，GPL-2.0，master 分支）。
3. **CI 能力矩阵**：C++/CMake/Qt ✅（qtbase/qtdeclarative 均已在制品仓，
   kirigami/actiona 等 Qt6 应用先例已合并）。
4. **上游测试 N=0**：fingerterm 上游**没有任何测试**（无 tests/ 目录、无
   ctest、无 CI 配置）——N=注册数实测=0。test_package 采用结构性验证
   （ELF/符号/DT_NEEDED/重定位）替代，见下。

## 平台差异诊断与修复（Qt5→Qt6 + OHOS）

| # | 断裂点 | 修复 |
|---|--------|------|
| 1 | qmake 工程（fingerterm.pro），OHOS Qt6 栈无 qmake 构建支持 | 新增顶层 CMakeLists.txt（同一源文件清单、同一 install 布局 share/fingerterm） |
| 2 | `#include "qplatformdefs.h"`（Qt5 qmake 时代头，Qt6 conan 包不装） | 改 `<QtGlobal>` |
| 3 | `QTextCodec`（Qt6 移除，ptyiface 三个用点） | `QStringDecoder`/`QStringEncoder`（QStringConverter 族；unique_ptr 持有——QStringConverter 删除拷贝赋值；charset 未知名回落 UTF-8 与原 codecForName 语义一致） |
| 4 | `QScreen::setOrientationUpdateMask`（Sailfish 私有扩展，上游 Qt6 无） | 整段删除（orientation 逻辑 QML 层仍工作） |
| 5 | `import QtQuick.XmlListModel 2.0`（Qt6 模块更名） | `import QtQml.XmlListModel`（qtdeclarative 包内 qml/QtQml/XmlListModel 实测存在） |
| 5b | `XmlRole`（Qt6 更名 XmlListModelRole）+ `query` XPath 属性（改 elementName/attributeName） | 三行 XmlRole → XmlListModelRole + elementName 映射 |
| 5c | `XmlListModel.xml` 内联串属性（Qt6 移除，只留 source URL） | C++ 新增 `Q_INVOKABLE QUrl userMenuXmlUrl()` 返回 data: URL（QUrl::toPercentEncoding），QML `source:` 绑定 |
| 6 | `QString::KeepEmptyParts`（Qt6 移除） | `Qt::KeepEmptyParts`（Qt::SplitBehavior 命名空间迁移，语义精确等价） |
| 6b | `QString::append(int)`（Qt6 隐式 QChar 转换移除） | `append(QChar(int))` |
| 6c | `QByteArray buf` 混用 append(QChar)+indexOf(QString)（Qt6 QByteArray↔QString 隐式转换移除） | grabURLsFromBuffer 的 buf 改 `QString` |
| 6d | `QFont::ForceIntegerMetrics`（Qt6 移除） | setStyleHint 去掉该 flag |
| 6e | `static const char ch_ESC` 类内初始化被 `fmt.arg(const char&)` odr-use（ld: undefined symbol） | terminal.cpp 补类外定义 `const char Terminal::ch_ESC;` |
| 7 | `Screen.angleBetween`（疑似 Qt6 移除） | **实测仍在**（qtdeclarative 6.11.1 plugins.qmltypes QQuickScreenAttached），无需改 |
| 8 | `LIBS += -lutil`（glibc 惯例） | OHOS musl sysroot 有 libutil.a stub（符号在 libc），CMake find_library 兼容保留 |
| 9 | lupdate/lrelease 翻译目标（qmake extra targets） | 不移植：翻译目录不生成，qsTrId 回落英文原文；TRANSLATIONS_PATH 指向部署目录（用户可放目录） |
| 10 | `DEPLOYMENT_PATH=/usr/share/fingerterm` 硬编码 | CMake 变量化 → conan 包 `<pkg>/share/fingerterm` |
| 11 | forkpty/termios（OHOS musl pty 支持疑虑） | **实测可用**：sysroot pty.h 声明 forkpty/openpty；本机编译运行 ptytest 通过（child echo 回 parent）；python pty.fork 亦通过 |
| 12 | Qt host 工具（moc 等）缺 libc++_shared.so | generate() 注入 SDK `llvm/lib/aarch64-linux-ohos` 到 LD_LIBRARY_PATH（attica E077 同款） |
| 13 | conan 沙箱产物沙箱外 exec 报 EPERM（ELF 签名校验） | binary-sign-tool -selfSign 1 重签后可执行（设备实测验证用） |

## 测试（上游 N=0，自建结构性测试）

上游 fingerterm 无测试目录/无 ctest/无 CI ——「上游测试 N=注册数」= 0。
test_package 自建五层验证（R34 非空壳）：

1. **布局**：bin/fingerterm + share/fingerterm/{Main.qml,Keyboard.qml,...} +
   data/{english.layout,menu.xml} + icons/ 全存在
2. **ELF**：64-bit LE AARCH64、musl loader（test_fingerterm.cpp 手写 ELF 解析）
3. **符号**：Terminal/TextRender/PtyIFace/KeyLoader + keyPress 全部在符号表
   （证明 VT 引擎、渲染器、pty 层、键盘加载器真实编入，非 stub）
4. **DT_NEEDED**：libQt6Quick/Qml/Gui/Core（Qt Quick 链路完整）
5. **重定位**：LD_BIND_NOW=1 + QT_QPA_PLATFORM=offscreen 启动（动态链接器
   全量重定位无未解析符号；无显示环境走 Qt 正常报错路径退出）

## 设备实测运行验证（重签后）

conan create 产物经 binary-sign-tool 重签、`QT_QPA_PLATFORM=offscreen` +
`QML2_IMPORT_PATH=<qtdeclarative>/qml` 启动实测：

- ✅ forkpty 成功，QML 引擎完整加载 Main.qml → Keyboard/Menu/XmlListModel 全链路
- ✅ 无 "no root object"/"qml error"（QtQuick.Window/QtQml.XmlListModel 模块解析正常）
- ✅ TextRender（QQuickPaintedItem）注册并实例化
- ⚠ Nemo.Configuration（Sailfish 私有模块）不存在的警告走上游容错分支（cornerRounding/notch 回落 0）
- ⚠ 退出原因：pw_shell=/bin/false → forkpty 子 shell 立即退出 → SIGCHLD → qApp->quit()（上游设计行为；设备上有真实登录 shell 时正常驻留）

## 路径 B 判定（四道关卡）

1. **可跨库复用知识**：✅ Qt5→Qt6 源码级 API 迁移组合方案（9 个迁移点 + qmake→CMake + EPERM 重签验证方法链）——任何 Qt5 QML 应用（qmake 工程）移植 ohpcd Qt6 栈都会命中同族断裂点
2. **知识图谱查重**：✅ E437/E438/E440/E441（cmake 组件查找）、E323/E343（Qt6 模块构建）、E077（签名重签）均不覆盖"源码级 API 迁移"层；无 Qt5→Qt6 移植条目
3. **证据扎实**：✅ 本地 conan create 全绿（test_package 五层验证）+ 设备 QML 全链路实跑证据
4. **PR open + 申请人=认领人**：✅ 待 PR 创建后挂 B issue

**结论：够格**。草稿：`knowledge/drafts/E551-draft-J669.kv/.md`（成对），随本 PR 提交。

## 已知限制

1. **GUI 运行时验证受限**：CI worker 无显示，offscreen 模式只能验证动态链接
   与 QML 引擎装载路径的早期阶段；完整 VT 渲染需设备人工验证（far2l 同款限制）。
2. **/dev/pts 权限**：普通 shell 下 /dev/pts/ 不可列举（Permission denied），
   但 forkpty() 实测可用（ptmx 通过 syscall 打开）——运行时以实测为准。
3. **翻译缺失**：lrelease 未运行，UI 英文原文显示（qsTrId 回落），非功能缺失。
4. **orientationMask 设置项**：OHOS 下不生效（Sailfish 私有 API guard），
   设置项仍可读写（QSettings 层），仅不改变行为。

## 源码

- 官方 tarball：`https://github.com/sailfishos/fingerterm/archive/refs/tags/1.4.16.tar.gz`
- 解压根目录：`fingerterm-1.4.16/`
- 补丁：`patches/0001-Port-fingerterm-to-Qt6-CMake-for-HarmonyOS-PC.patch`（6 文件，+154/-13）
