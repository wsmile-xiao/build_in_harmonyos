## PR 信息
- **三方库名称**：libkdegames（不含版本号！rule1+软件名校验）
- **上游版本**：26.04.0
- **上游仓库地址**：https://invent.kde.org/games/libkdegames
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无（复用仓内 KF6 6.18 系既有打法：knewstuff/6.18.0 配方骨架 + CMAKE_PREFIX_PATH 喂包路径模式）

> 源码包 URL（conandata.yml）: https://invent.kde.org/games/libkdegames/-/archive/v26.04.0/libkdegames-v26.04.0.tar.gz （SHA-256 见 conandata.yml）

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 2 | CTest（ecm_add_tests）src/private/tests/：kgamesvgdocumenttest、kgamepropertytest（ctest -N 实测 Total Tests: 2） |
| 集成测试 | 0 | 上游无 |
| 其他测试 | 1 | tests/kgamepopupitemtest：上游仅编译为可执行文件（手动 GUI 工具），未 add_test 注册，不计入 ctest |
| **合计** | **2** | ctest -N 实测口径（上游注册数） |

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 2 | 不变 | 同上游 BUILD_TESTING=ON 全量注册并实跑 |
| 集成测试 | 0 | 不变 | 上游无 |
| **鸿蒙特有测试** | 1 | 新增 | test_package 消费者测试：KGameClock/KGameTheme/KGamePopupItem 真实 API 调用（offscreen 平台运行） |
| **合计** | **3** | +1 | 上游 2 + 鸿蒙消费者测试 1 |

## 上游测试用例减少原因
无减少。上游注册 2 项全部实跑通过（2/2，100%）。

## 上游测试用例修改说明
- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在修改（逐条：文件路径+修改原因+修改内容）

## 补全测试用例说明
- [ ] **否**，上游已有测试覆盖
- [x] **是**，上游无消费者级测试，适配后补全（补全范围+原因+新增文件清单）
  - 补全范围：test_package/ 消费者冒烟——链接 KDEGames6 库并真实调用 KGameClock（restart/pause/resume/setTime/timeString/seconds）、KGameTheme（identifier/name/license/author 元数据回写、readFromDesktopFile 拒绝非存在路径）、KGamePopupItem（QGraphicsScene 注册、setMessageTimeout/setMessageOpacity、hidesOnMouseClick 回写、forceHide）API，offscreen 平台运行验证。
  - 原因：上游 test_package 无消费者级集成验证（上游仅库内单元测试）。
  - 新增文件清单：archives/l/libkdegames/26.04.0/test_package/ 下 conanfile.py、CMakeLists.txt、test.cpp、MANIFEST.yml

## 验证结果
- 编译状态：通过（conan create 全绿）
- 上游测试用例通过率：2/2（100%）
- 新增测试用例通过率：1/1（100%）

### 编译验证
- 编译器: clang 15 (aarch64-unknown-linux-ohos)
- 编译状态: 成功
- 构建系统: CMake（ECM/KDE 标准工具链）
- 配置选项: BUILD_TESTING=ON、KF_IGNORE_PLATFORM_CHECK=TRUE、KF_SKIP_PO_PROCESSING=ON、BUILD_SHARED_LIBS=ON

### 产物验证
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | ✅ | libKDEGames6.so + libKDEGames6Private.so（SOVERSION 6）+ org.kde.games.core QML 模块 + carddecks SVGZ 资源 |
| 产物存在性 | ✅ | conan create 验证（含安装产物完整性） |
| ELF 格式 | ✅ | aarch64-unknown-linux-ohos |
| 运行测试 | ✅ | 2/2 上游 ctest + 1/1 消费者测试 |

### 上游测试实测记录（本地联网补跑，clancyxie 口径）
- 实测命令：conan create（BUILD_TESTING=ON）→ ctest --output-on-failure
- 实测输出：
  - `1/2 Test #1: libkdegamesprivate-kgamesvgdocumenttest ... Passed`
  - `2/2 Test #2: libkdegamesprivate-kgamepropertytest ... Passed`
  - `100% tests passed, 0 tests failed out of 2`
- 配置期检查：上游 try_compile(check-libsndfile-capabilities) 对 conan libsndfile/1.2.2 包通过（Ogg/Vorbis 枚举能力验证）。
- 未执行项说明：tests/kgamepopupitemtest 为上游手动 GUI 可执行（未注册 ctest），未纳入自动统计——与上游 CI 行为一致。

## 补丁说明
无补丁（选项配置适配）。

## 依赖
- qtbase/6.11.1（已发布）
- qtdeclarative/6.11.1（已发布）
- qtsvg/6.11.1（已发布）
- karchive/6.18.0（已发布，override 钉版）
- kcolorscheme/6.18.0（已发布）
- kcompletion/6.18.0（已发布）
- kconfig/6.18.0（已发布）
- kconfigwidgets/6.18.0（已发布）
- kcoreaddons/6.18.0（已发布）
- kdnssd/6.29.0（已发布）
- kguiaddons/6.18.0（已发布）
- ki18n/6.18.0（已发布）
- kiconthemes/6.18.0（已发布）
- knewstuff/6.18.0（已发布）
- kxmlgui/6.18.0（已发布）
- openal-soft/1.25.2（已发布）
- libsndfile/1.2.2（已发布）
- 构建依赖：ecm/6.26.0（已发布）

## 补充说明
- 版本号策略：26.04.0 为上游 KDE Gear 26.04 正式版本号
- KF6 依赖闭包按上游 26.04.0 .kde-ci.yml 组件集（Archive/ColorScheme/Completion/Config/ConfigWidgets/DNSSD/GuiAddons/IconThemes/I18n/NewStuff/XmlGui）取 6.18.0 系（kdnssd 6.29.0），与仓内 KDE Games 链一致
- karchive/6.18.0 以 override=True 钉版：最新 kiconthemes/6.18.0 配方 revision 依赖 karchive/6.19.0，与 knewstuff/6.18.0 的 karchive/6.18.0 冲突；钉版保证全图一致
- 消费者测试中 KGamePopupItem::showMessage() 未调用：该方法启动 QVariantAnimation 需要运行中的事件循环与真实 paint engine，headless offscreen 进程无 app.exec() 时段错误；scene 注册/属性/forceHide API 均已覆盖验证
- 已知限制：QFontDatabase 字体目录警告（qtbase 包未带 fonts/，不影响库功能与测试）
