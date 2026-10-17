# ktextaddons 2.0.2 适配笔记（HarmonyOS PC / aarch64-linux-ohos）

## 适配概况

- KDE 文本编辑增强组件库（kpimtextedit / akonadi 下游链的依赖件），上游仓库
  <https://invent.kde.org/libraries/ktextaddons>，发布 tarball
  <https://download.kde.org/stable/ktextaddons/ktextaddons-2.0.2.tar.xz>
  （sha256 `0d7f82a976ef682f45822b221e2f15cefc0039488bc8c700a6b0e7594aaebdea`）。
- 构建系统：CMake + ECM（KDE Frameworks 6 线），`QT_REQUIRED_VERSION=6.9.0`、
  `KF_MIN_VERSION=6.20.0`、`QT6KEYCHAIN_LIB_VERSION=0.15.0`。
- 产物：12 个共享库 + 翻译引擎插件 + 文本自动生成插件：

  | 库 | 说明 |
  |----|------|
  | KF6TextAddonsWidgets | SlideContainer、特殊字符对话框、更新检查、whatsnew |
  | KF6TextAutoCorrectionCore / Widgets | 自动更正核心与控件 |
  | KF6TextEmoticonsCore / Widgets | 表情/emoji 模型与选择控件 |
  | KF6TextTranslator | 翻译引擎框架 + bing/google/lingva/yandex/deepl/libretranslate 插件 |
  | KF6TextGrammarCheck | Grammalecte / LanguageTool 检查框架 |
  | KF6TextUtils | 大小写/规范化等文本工具 |
  | KF6TextCustomEditor | PlainTextEditor / RichTextEditor / RichTextBrowser |
  | KF6TextAutoGenerateText | AI 文本生成框架 + 各 provider 插件 |
  | KF6TextSpeechToText | 语音转文字（Qt Multimedia） |
  | KF6TextEditTextToSpeech | 文本转语音（Qt6TextToSpeech） |

## W0 依赖预检（全部用 conan download / conan install --build=never 验证）

前置结论：**ohpcd 上 KF6 各版本线的二进制并不互相兼容**，必须选一条完整可消费的线。

- 候选线对比（`conan install --build=never`）：
  - KF6 **6.26 线**：全部命中已发布二进制 ✅ 采用本线。
  - KF6 6.18 线：`ktextwidgets/6.18.0` 与 6.18.0.1/.2 变体是用 `qtbase/6.11.1.3`
    构建的（pid 带 cups/wayland/freetype 等重依赖链），而 karchive/kcodecs/
    kguiaddons/kitemviews/kservice/ksyntaxhighlighting/kiconthemes 只有用
    `qtbase/6.11.1` 构建的"轻"二进制，二者无法在同一张图里同时命中 ❌。
  - 结论：`ktextwidgets`（唯一消费点 = TextAutoGenerateTextLineEdit 的 KTextEdit
    聊天输入框）在该线内无法消费，改用 QTextEdit（补丁 0007），并因此不需要
    降低上游 `KF_MIN_VERSION`（6.26 ≥ 6.20，无版本 hack）。
- Qt6 模块供给：`qtbase/6.11.1` 是 `FEATURE_sql=OFF / FEATURE_dbus=OFF`，
  而 2.0.2 顶层要求 `Qt6 Sql`（textautogeneratetext 聊天数据库）与 `Qt6DBus`
  （非 Win/Apple 平台）。因此 Qt 提供者用 **qtbase-sql-dbus/6.11.1**
  （akonadi 25.12.3 先例），KF6 6.26 包仍依赖 qtbase/6.11.1，两棵树共存，
  在 CMAKE_PREFIX_PATH / CMAKE_LIBRARY_PATH / CMAKE_INCLUDE_PATH 中把
  qtbase-sql-dbus 放在最前。
- 其它已发布依赖：qtmultimedia/6.11.1（Qt6::MultimediaWidgets，textspeechtotext）、
  qttexttospeech/6.11.1（textedittexttospeech）、qtkeychain/0.14.2（ollama/deepl
  等插件的凭据存储，其二进制正好依赖 qtbase-sql-dbus/6.11.1，与本配方一致）、
  kio/6.26.0（KIOCore-only）、kcrash/6.26.0、karchive/kcolorscheme/kconfig/
  kcoreaddons/kguiaddons/ki18n/kitemviews/kiconthemes/kservice/
  ksyntaxhighlighting/kwidgetsaddons/sonnet 6.26.0、openssl/3.5.6.1、
  zstd/1.5.7.1、zlib/1.3.2、tool_requires ecm/6.26.0。

## 平台适配要点

1. **Qt 双树与 Qt 模块查找**（无源码补丁）：qtbase-sql-dbus 作为 Qt 提供者；
   `QT_ADDITIONAL_PACKAGES_PREFIX_PATH` 指向 qtmultimedia/qttexttospeech/qtsvg/
   qtshadertools 包，供 Qt6Config.cmake 解析 `Qt6::MultimediaWidgets` 等组件。
2. **KIO 侧**：ohpcd kio 为 KIOCORE_ONLY（无 KIOWidgets/KIOGui/KIOFileWidgets）。
   `BUILD_KIO_SUPPORT=ON` 保留 KIOCore（更新检查 job 可用），widgets 侧消费点全部
   移除：web-shortcut 菜单（本来就由 `HAVE_KTEXTADDONS_KIO_SUPPORT` 守卫，
   未定义时自动关闭）、KFileWidget::getStartUrl、KIO::ApplicationLauncherJob、
   KUrlRequester（补丁 0003/0004/0008/0009）。
3. **ktextwidgets 缺席**：TextAutoGenerateTextLineEdit 由 KTextEdit 改为 QTextEdit
   （补丁 0007），保留发送/按键处理，去掉该控件上的拼写检查与查找替换集成。
4. **Qt6Keychain 版本**：上游要求 0.15.0，ohpcd 仅 0.14.2，且 2.0.2 使用的
   `QKeychain::Read/Write/DeletePasswordJob`、`Job::finished`、`Error::NoError`
   均为 0.14 已有 API，故补丁 0001 降低版本要求到 0.14.2（实测编译链接通过）。
5. **构建参数**：`KF_IGNORE_PLATFORM_CHECK=TRUE`、`KF_SKIP_PO_PROCESSING=ON`
   （lconvert 在本平台加载 libQt6Core 失败，sonnet 先例）、
   `BUILD_DESIGNERPLUGIN=OFF`（Qt6UiPlugin 未发布）、`BERGAMOT_TRANSLATOR_PLUGIN=OFF`、
   `SPEAK_TO_TEXT_VOSK_PLUGIN=OFF`、`BUILD_QUICK=OFF`、C++20。
6. **SONAME 旗标**：CMake 无 Platform/HarmonyOS 模块，默认不设
   `CMAKE_SHARED_LIBRARY_SONAME_*`，安装出的库会没有 DT_SONAME（消费者会把构建目录
   相对路径写进 DT_NEEDED）。配方显式恢复 `-Wl,-soname,`。
7. **相对 DT_NEEDED 处理**：若干已发布 KF6/Qt 包记录了构建布局相对路径
   （`../../bin/libKF6ConfigCore.so`、`../../bin/libKF6I18n.so`、
   `../../bin/libKF6SonnetCore.so`、`../../lib/libQt6Multimedia.so`），musl 加载器
   按进程 CWD 解析含斜杠的 DT_NEEDED（不走 LD_LIBRARY_PATH）。配方在运行上游测试前
   解析所有相关 ELF 的相对 DT_NEEDED，并在每个 CTest 测试目录及其 bin/lib 变体下
   补齐符号链接（kcalendarcore / ktextaddons 1.5.0 先例）。
8. **ECMAddTests 插件路径覆盖**：`ecm_add_test` 会给每个测试烧入
   `QT_PLUGIN_PATH=<build>/bin`，覆盖继承的环境变量，因此把测试运行需要的插件
   投放到 `<build>/bin`：`kf6/translator`、`kf6/textautogeneratetext`
   （引擎加载器按 `libraryPaths()+"/kf6/<component>/"` 扫描）、
   `sqldrivers/libqsqlite.so`（聊天数据库测试）、`platforms`（offscreen）。

## 上游测试实测（本机 conan 构建树，2026-10-10）

- 上游测试入口：CMake/CTest（ECMAddTests 注册），`ctest -N` 实测 **190 项注册用例**，
  分布在 37 个 autotests 目录。
- 真实执行结果（`ctest --output-on-failure --no-tests=error --timeout 180`，
  排除 2 项环境限制用例）：

  | 指标 | 数值 |
  |------|------|
  | 注册用例 | 190 |
  | 执行用例 | 188 |
  | 通过 | 188（执行用例通过率 100%） |
  | 失败 | 0 |
  | 跳过 | 0 |
  | 排除（OHOS 沙箱环境限制） | 2 |
  | 总耗时 | 约 155 s |

- 排除用例与逐项技术原因：
  - `texttospeech-texttospeechactionstest`：断言 play/stop 动作 `icon()` 非空
    （`QIcon::fromTheme`），OHOS 沙箱没有图标主题（`QFontDatabase` 亦报
    "Cannot find font directory"），`icon().isNull()` 确定性为 true
    （ktextaddons 1.5.0 / kio 6.26.0 先例，同一类断言）。
  - `translator-translatorwidgettest`：`TranslatorWidget` 构造时初始化 google 引擎
    并拉取引擎语言列表（真实 HTTP），沙箱无出站网络，`QEventLoop` 驱动的请求永不返回
    （实测 120 s 超时；ktextaddons 1.5.0 / kio 6.26.0 先例）。
- 其余日志证据：`<build>/Testing/Temporary/LastTest.log`；分类失败修复记录：
  初次运行 12 项失败（相对 DT_NEEDED 未补链 6 项 + SQL 驱动插件未投放 3 项 +
  web-shortcut 断言 3 项），补齐链接/插件与断言后降到 2 项环境限制。

## test_package（消费者视角）

- `test_package/test.cpp`：真实调用 `TextEmoticonsCore::EmoticonUnicodeUtils::
  escapeUnicodeEmoji/emojiFontName`、`TextUtils::ConvertText::normalize/upperCase/
  lowerCase`、`TextAddonsWidgets::SlideContainer`（offscreen），7/7 断言通过。
- `test_package/ohos_test.cpp`（**鸿蒙特有测试**）：安装产物层面的平台断言 ——
  逐个解析安装前缀下每个共享库的 ELF64 `.dynamic` 段，断言 DT_SONAME 存在且为纯
  文件名（验证第 6 条 soname 适配）、断言 12 个组件库全部安装、断言
  `kf6/translator` 插件目录与插件存在、offscreen 下真实构造 SlideContainer
  并驱动 slideHeight。

## 与既有先例的差异

- 与 1.5.0（kconfigwidgets 6.18 + 6.26 混线）不同：2.0.2 的依赖集合完整落在
  KF6 6.26 线内，无需任何跨线 override，避免了 6.18/6.26 二进制互相不兼容的问题。
- 与 1.8.0（只编 textutils 子集）不同：本适配编译全部 12 个组件与全部插件族，
  仅在 KIO widgets / ktextwidgets 两个不可消费点上做等价的 API 替换。

## 本机构建环境备注（影响复现方式，不影响配方内容）

- 本机文件系统**不支持 FIFO**（`mkfifo` 在 `$HOME`/`$HOME/tmp`/`/tmp` 均返回 EPERM），
  Conan 默认的 Unix Makefiles 生成器因此无法建立 jobserver
  （`make: jobserver mkfifo: ... Operation not permitted`），编译退化为单线程，
  完整构建耗时 > 6 小时并触发工具侧 1 小时超时。
- 本地验证改用 `-c tools.cmake.cmaketoolchain:generator=Ninja -c tools.build:jobs=8`
  （`conan create` 仅多两个 conf 参数，配方本身与生成器无关）：1522 个构建目标约 40 分钟完成，
  构建/测试/打包/test_package 全绿。
- 该 conf 只影响本地复现速度；CI 侧沿用自身环境，配方不依赖 Ninja。
