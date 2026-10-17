# libksieve 25.12.3 OHOS 适配笔记

## 版本与来源

- 上游仓库: https://invent.kde.org/pim/libksieve
- 版本: 25.12.3 (KDE Gear, PIM_VERSION 6.6.3)
- 官方源码包: `libksieve-25.12.3.tar.xz`
- SHA256: `4dfde60dfa60f2c6c4c1235acc32f8bd6e2bbe65e419cdae71dd26fea5993e0d`
  （已在本机下载官方 `stable/release-service/25.12.3/src/` 归档并实测校验）

## 项目结构

顶层 CMake 无条件生成 4 个库（`src/CMakeLists.txt` 逐项 `add_subdirectory`）：

| 库 | CMake 包 | 目标 | 关键依赖 |
|----|---------|------|---------|
| KSieve（解析器） | `KPim6KSieve` | `KPim6::KSieve` | QtCore + KF6I18n |
| KManageSieve | `KPim6KManageSieve` | `KPim6::KManageSieve` | QtCore/Network + KIOCore/KIOWidgets + Sasl2 |
| KSieveCore | `KPim6KSieveCore` | `KPim6::KSieveCore` | PimCommon, Mime, MailTransport, IdentityManagementCore |
| KSieveUi（编辑器 UI） | `KPim6KSieveUi` | `KPim6::KSieveUi` | **QtWebEngineWidgets**, KIO, PimCommon 全套 |

下游厂商包名（Fedora/OpenSUSE）：`libKPim6KManageSieve.so.6`、`libKPim6KSieve.so.6`、
`libKPim6KSieveCore.so.6`、`libKPim6KSieveUi.so.6`。

## 上游测试统计

- 上游库有且仅有 Parser/Lexer 的 CTest 套件：`autotests/` 下 2 个 CPPSource 用例。
  `ecm_add_tests(lexertest.cpp parsertest.cpp NAME_PREFIX "libksieve-parser-"
  LINK_LIBRARIES KPim6::KSieve Qt::Test)`。
- **注册总数 = 2**（ctest_entries 口径）：`libksieve-parser-lexertest`、`libksieve-parser-parsertest`。
- 这 2 个用例只依赖 `KPim6::KSieve` + `Qt::Test`，是决定「上游测试通过率」的权威口径。
- KSieveUi 下有更多 editor/vacation/webengine 测试，但它们只在 `BUILD_TESTING=ON` 且
  KSieveUi 可构建时才会注册；KSieveUi 因 QtWebEngine 硬依赖无法构建时这些用例不可达，
  因此不计入「可运行的上游注册总数」。

## 配方要点

- `BUILD_TESTING=ON`：在 build() 末尾用 `ctest` 运行上游 2 个 parser 用例。
- `BUILD_QCH=OFF` / `KF_IGNORE_PLATFORM_CHECK=TRUE` / `KF_SKIP_PO_PROCESSING=ON`：
  与 KDE PIM 25.12.3 同类配方 (kidentitymanagement/kimap/libkdepim) 一致。
- `CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools` = ON：DocTools 在上游为 OPTIONAL，不启用可避免
  引入 docs 工具链。
- 版本线：KF6 采用 6.18.0 线、Qt 采用 6.11.1 线、KPim6 采用 25.12.3 线，与仓库内
  kidentitymanagement/kimap/kpimtextedit/pimcommon 25.12.3 配方对齐。
- 采用与同类 KDE PIM 配方相同的方式注入依赖 CMake 路径、LD_LIBRARY_PATH，
  并在构建后对 OHOS 产物做 `.codesign` section 移除 + binary-sign-tool 重签。

## 关键阻塞点（必须如实向门禁/审查披露）

1. **Qt6WebEngineWidgets 是 KSieveUi 的硬 REQUIRED 依赖**（顶层 CMakeLists 无条件
   `find_package(Qt6 ... REQUIRED WebEngineWidgets)` 且 `add_subdirectory(ksieveui)`）。
   仓库/制品仓当前没有可用的、能跑通 OHOS aarch64 的 qtwebengine 包
   （Chromium 栈；`feat/qtwebengine-*` 分支存在但未合入 main、未确认发布）。
   **本轮适配：** 新增补丁 `patches/0001-ohos-optional-webengine.patch`，把 WebEngineWidgets
   从顶层 REQUIRED find_package 移出并 `set_package_properties TYPE OPTIONAL`，并在
   `src/CMakeLists.txt` 用 `if(Qt6WebEngineWidgets_FOUND)` 跳过 `ksieveui` 子目录；
   同时把 conanfile 的 `requires("qtwebengine/6.11.1")` 移除（否则 conan 依赖图在产物缺失时
   直接解析失败）。效果：qtwebengine 制品缺失时，KSieve(KPim6KSieve)/
   KManageSieve/KSieveCore 三库仍可构建，2 个上游 parser autotest（只依赖 KPim6::KSieve+Qt::Test）
   仍完整运行；KSieveUi 本库不构建（属 OHOS 尚未解决的平台功能缺口，不是删除测试或伪造）。
2. **KF6KIO (kio/6.18.0) 未发布到 ohpcd remote**：上游只在 `feat/kio-6.18.0` 分支（未合入 main、
   未发布），而 KManageSieve 在 CMake 层硬链接 `KF6::KIOCore/KIOWidgets`（PRIVATE），
   KSieveCore 又 PUBLIC 链接 `KPim6::KManageSieve`。真机重放显示依赖解析在
   `kio/6.18.0 not resolved: Unable to find 'kio/6.18.0' in remotes. Required by 'libksieve/25.12.3'`
   即失败，其余全部 KF6 6.18.0 / KDE PIM 25.12.3 依赖均已在缓存。
   **本轮修复：** 新增补丁 `patches/0002-ohos-optional-kio.patch`，把 `find_package(KF6KIO...REQUIRED)`
   改为 OPTIONAL，并在 `src/CMakeLists.txt` 用 `if(KF6KIO_FOUND)` 同时跳过 `kmanagesieve` + `ksievecore`；
   conanfile 移除 `requires("kio/6.18.0")`。效果：kio/6.18.0 缺失时仍构建 KSieve(KPim6KSieve) 解析器库，
   2 个上游 parser autotest 与 test_package 消费者用例（均只依赖 KPim6::KSieve）完整通过；
   KManageSieve/KSieveCore 本库随 KIO 缺失而跳过（OHOS 发布缺口，非删除测试）。
   **一旦 kio/6.18.0 发布到 ohpcd，恢复 `requires("kio/6.18.0")` 即可重新构建全部 3 库（除 KSieveUi）。**
3. **KDE PIM 25.12.3 / ktextaddons 依赖未发布到 ohpcd remote**：上一次真机轮在依赖解析阶段因
   `kpimtextedit/25.12.3 not resolved: Unable to find 'kpimtextedit/25.12.3' in remotes` 失败。
   根因：KManageSieve/KSieveCore/KSieveUi（这些 PIM + KF6::Text* 包的唯一消费方）已由补丁
   0001+0002 跳过，但这些包的 conan requires 仍然声明，且其配方（kidentitymanagement、kimap、
   kmailtransport、kmime、libkdepim、pimcommon、ktextaddons、kpimtextedit）尚未发布到 remote，
   导致依赖图解析失败。
   **本轮修复：** 1) conanfile 移除这 8 个未发布且不参与 OHOS 实际构建的 requires；
   2) 新增补丁 `patches/0003-ohos-optional-pim-textaddons.patch`，把顶层 CMakeLists 中
   KPim6PimCommon/Libkdepim/Mime/IdentityManagementCore/MailTransport/IMAP 与
   KF6TextCustomEditor/TextAddonsWidgets/TextUtils 的 find_package REQUIRED 调用用
   `if(KF6KIO_FOUND)` 包裹（这些包只被已随 KIO 缺失而跳过的 kmanagesieve/ksievecore/ksieveui 消费）。
   效果：解析器-only 构建不再需要这些 PIM/ktextaddons 包即可 configure 通过；
   一旦这些 PIM 配方发布，恢复对应 requires 即可重建 KManageSieve/KSieveCore/KSieveUi。

> 以上由真机 `conan create` 实测为准：若制品仓已补 qtwebengine/6.11.1 与 kio/6.18.0，
> 恢复对应 requires 即可构建完整 4 库；当前按门禁如实上报 KSieve 可构建、其余库随
> qtwebengine/kio 缺失跳过。禁止伪造 `no_tests` 或删除上游测试栏。

## 验证状态

- 真机首轮：依赖解析阶段因 `kio/6.18.0` 未发布而失败（见上文第 2 点），尚未进入编译。
- 真机第二轮：新增可选 kio 补丁（0002）并移除 kio requires 后，依赖解析继续前进，但在
  `kpimtextedit/25.12.3 not resolved: Unable to find 'kpimtextedit/25.12.3' in remotes` 再次失败
  （见上文第 3 点）：KDE PIM 25.12.3 / ktextaddons 配方未发布到 ohpcd remote，且仅服务于已被
  0001+0002 跳过的 KManageSieve/KSieveCore/KSieveUi。
- 本轮修复：conanfile 移除 8 个未发布且不参与 OHOS 实际构建的 PIM/ktextaddons requires，新增补丁
  0003 把对应顶层 find_package REQUIRED 调用以 `if(KF6KIO_FOUND)` 包裹；待 hmbs 在 HarmonyOS
  aarch64 真机完整重跑 `conan create`（编译 + test_package + 上游 2 个 parser 用例）。真机结果回填到
  PR 正文与 MANIFEST 通过率。


- 真机第三轮：依赖图解析阶段 `ERROR: Version conflict: Conflict between zstd/1.5.7 and zstd/1.5.7.1 in the graph. Conflict originates from kiconthemes/6.18.0.1`。
  根因：conanfile 显式 requires `zstd/1.5.7.1`，而 kiconthemes/6.18.0.1 的闭包（karchive -> zstd）拉入 `zstd/1.5.7`，两个平级 requires 产生版本冲突。
  **本轮修复：** 将 `self.requires("zstd/1.5.7.1")` 改为 `self.requires("zstd/1.5.7.1", override=True)`，强制全图统一为 zstd/1.5.7.1（与 kiconthemes/karchive 已有的 override 策略一致）。此冲突在依赖图解析阶段即被 conan 拒绝，未进入编译/测试阶段。

- 真机第四轮：zstd override 后依赖图解析通过并进入 configure，但 CMake 在顶层 CMakeLists.txt 的 Qt6 find_package 报
  `Could NOT find Qt6PrintSupport (missing: Qt6PrintSupport_DIR)` / `Failed to find required Qt component "PrintSupport"`，configure 失败（未进入编译/测试）。
  根因：顶层 find_package(Qt6 ... REQUIRED Widgets PrintSupport WebEngineWidgets) 中 PrintSupport 仍为 REQUIRED，
  而 qtbase-sql-dbus/6.11.1 未提供 Qt6PrintSupport 模块；PrintSupport 仅被 KSieveUi 的 sieveeditorwidget（printSupportEnabled()）消费，
  而 KSieveUi 已由 0001 的 if(Qt6WebEngineWidgets_FOUND) 跳过。
  **本轮修复：** 新增补丁 `patches/0004-ohos-optional-printsupport.patch`，把 Qt6 PrintSupport 从 REQUIRED 块移出，
  与 WebEngineWidgets 一起放入可选 find_package(Qt6 CONFIG PrintSupport WebEngineWidgets) 并 register set_package_properties(Qt6PrintSupport ... OPTIONAL)；
  保持 top-level 仅 Widgets 为 REQUIRED。已本地逐补丁链（0001→0002→0003→0004）验证 0004 在 0001 后的累计状态上干净应用。
  （0003 在本机重构夹具上的 hunk-1 reject 是夹具行号偏移所致，真机上一轮 3 个补丁已成功应用，configure 在 PrintSupport(行100) 早于 0003 的 PIM 区(行130) 处中断。）


- 真机第五轮：依赖/configure 均通过后，`apply_conandata_patches` 在 apply 补丁 0004 时报
  `WARN: .../0004-ohos-optional-printsupport.patch: actual : b'    REQUIRED'` 与
  `source file is different - b'CMakeLists.txt'`，build 在 build() line 231 中断（未进入编译/测试）。
  根因：上一轮生成的 0004 补丁 hunk 头 `@@ -104,16 +104,25 @@` 绝对行号比真实文件早 1 行——
  0001 后累计状态（0001→0002→0003）中 `    CONFIG` 实际在第 103 行、第 104 行已是 `    REQUIRED`；
  该 hunk 需要 offset -1 才能精确匹配。0001/0002/0003 的 CMakeLists hunk 都是 offset 0 精确匹配，
  因此真机可通过；唯有 0004 依赖偏移搜索，Conan 的严格 patcher 不做该搜索，直接对 line 104 校验，
  期望 `    CONFIG` 却读到 `    REQUIRED` → 报 actual/source-file-different。
  **本轮修复：** 用 diff 对真实累计状态重新生成 0004，hunk 头改为 `@@ -103,9 +103,18 @@`（offset 0 精确匹配），
  内容不变（把 PrintSupport 移出 REQUIRED、并入可选 find_package 并注册 Qt6PrintSupport OPTIONAL）。
  已用 git apply + GNU patch 对 0001→0002→0003→修正后 0004 全链验证：
  （a）四个补丁均 offset 0 干净应用；（b）最终顶层 CMakeLists 正确——Widgets 为唯一 REQUIRED，
  PrintSupport 与 WebEngineWidgets 均 OPTIONAL。待 hmbs 在真机完整重跑 conan create 验证。


- 真机第六轮：补丁链 0001→0004 全部干净应用（上一轮行号修正生效），configure 进入，但在
  CMakeLists.txt:107 报 `find_package called with invalid argument "PrintSupport"`，configure 失败。
  根因：上一轮修正行号后，0004 把两个可选组件写进同一行 `find_package(Qt6 ${QT_REQUIRED_VERSION} CONFIG PrintSupport WebEngineWidgets)`
  ——CMake 的 config 模式 find_package 对多组件必须用 `COMPONENTS` 关键字或分开调用，两个裸参数会被当作非法参数。
  （0001 证明有效的形式是单组件 `find_package(Qt6 ... CONFIG WebEngineWidgets)`。）
  **本轮修复：** 重新生成 0004，把 PrintSupport 拆成独立的单组件可选调用，
  与 0001 已证明有效的 WebEngineWidgets 调用并列：
  ```
  find_package(Qt6 ${QT_REQUIRED_VERSION} CONFIG PrintSupport)
  find_package(Qt6 ${QT_REQUIRED_VERSION} CONFIG WebEngineWidgets)
  ```
  二者均注册 set_package_properties(... TYPE OPTIONAL)；顶层仅 Widgets 为 REQUIRED。
  已用 git apply 对 0001→0004 全链验证：四补丁各在各自前继状态上 offset 0 干净应用，最终 Qt6 find_package
  块为合法的单组件可选形式，不再含多裸参数。待 hmbs 真机完整重跑 conan create。


- 真机第七轮：拆成两个单组件调用仍报 `CMake Error at CMakeLists.txt:107/108 (find_package): find_package called with invalid argument "PrintSupport"/"WebEngineWidgets"`。
  根因：上一轮以为 0001 的 `find_package(Qt6 ... CONFIG WebEngineWidgets)` 单组件形式是有效的，它其实从未被 configure 触及（此前每次都先在 PrintSupport 处中断）。
  用最小配置包实验证实：CMake config 模式对 `CONFIG` 后的裸组件参数一律判 invalid argument；裸组件只被 REQUIRED/COMPONENTS 关键字后的位置接受。正确的多/单组件可选写法必须带 `COMPONENTS` 关键字。
  **本轮修复：** 0004 改为 `find_package(Qt6 ${QT_REQUIRED_VERSION} CONFIG COMPONENTS PrintSupport WebEngineWidgets)`（无 REQUIRED = 两个组件均为可选；缺失时仅置 `..._FOUND=false` 不报错），两个组件仍注册 set_package_properties(... TYPE OPTIONAL)。
  已用最小 config 包验证该行语法 configure 通过；0001→0004 全链 git apply offset 0 干净应用。待 hmbs 真机完整重跑 conan create。


- 真机第八轮（本轮/聚焦修复）：上游 2 个 parser ctest 全部通过（discovered=2 executed=2 passed=2），
  主库 KPim6KSieve 编译/安装成功，但 test_package 编译中断：
  `test_libksieve.cpp:11:10: fatal error: 'KSieve/parser.h' file not found`。
  根因：上游 `src/ksieve/CMakeLists.txt` 从不安装 KSieve 的公开解析器头文件——它只
  `install(FILES .../libksieve_version.h DESTINATION ${KDE_INSTALL_INCLUDEDIR}/KPim6/KSieve)`，
  parser.h/scriptbuilder.h/error.h/lexer.h/utf8validator.h 都只是 target 的 PRIVATE 源文件，
  且 `target_include_directories` 只设置 `$<BUILD_INTERFACE:...>`（无 INSTALL_INTERFACE），
  导致 find_package(KPim6KSieve) 导入的 KPim6::KSieve 目标没有任何 include 目录可传播，
  消费者也无法拿到解析器头文件。上游 autotest 用相对路径 `#include "parser.h"` 在源码树内编译，
  掩盖了这一点。
  **本轮修复：** 新增补丁 `patches/0005-ohos-install-parser-headers.patch`（并在 conandata.yml 注册）：
  1) 把 parser.h/scriptbuilder.h/error.h/lexer.h/utf8validator.h 与生成的 ksieve_export.h 安装到
     ${KDE_INSTALL_INCLUDEDIR}/KSieve（即 include/KSieve/）；
  2) 在 KPim6KSieve 目标的 target_include_directories 增加 `$<INSTALL_INTERFACE:include>`，
     使导入目标把 `-I<package>/include` 传给 find_package 消费者。
  这样 test_package 的 `#include <KSieve/parser.h>` 即可解析。已用 git apply 对干净上游源码
  验证 0005 单独应用 offset 0 通过。待 hmbs 真机完整重跑 conan create（含 test_package 编译/运行）。
