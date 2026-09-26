# grantlee 5.3.1 适配笔记

## 基本信息

| 项 | 值 |
|---|---|
| 软件 / 版本 | grantlee / 5.3.1 |
| 构建系统 | CMake（`cmake_minimum_required(VERSION 3.5)`，templates + textdocument 两大目标） |
| 上游仓库 | https://github.com/steveire/grantlee（tag `v5.3.1`） |
| 许可证 | LGPL-2.1-or-later（COPYING.LIB） |
| 补丁数 | 0（上游源码零修改——纯配方适配） |
| 产物 | libGrantlee5Templates.so + libGrantlee5TextDocument.so + 4 个插件（defaultfilters/defaulttags/i18n/loadertags，lib/grantlee/5.3/）+ 头文件 include/grantlee/ |
| 依赖 | qt5-qtbase/5.15.2（Qt5Core） |
| 状态 | **published（本机 conan create 绿：上游 ctest 10/10 + test_package 5/5，total failures = 0）** |

### 选型说明

- **Qt5 线而非 Qt6**：上游 `GRANTLEE_BUILD_WITH_QT6` 默认 FALSE；5.3.1 的
  find_package 写死 Qt5Core 5.2.0 REQUIRED（Qt6 需显式开关）。制品仓
  qt5-qtbase/5.15.2 与任务口径一致（任务要求"Qt5 模板引擎"）。
- **与 grantleetheme/25.12.3 不冲突**：那是 KF6 线的 KDE PIM 封装层
  （依赖 KF6::GrantleeTheme），本包是 Grantlee 引擎本体 Qt5 线——两者
  名称（grantlee vs grantleetheme）与依赖轨道均独立。

### 依赖豁免（W0 断链核查结论）

| 依赖 | 上游用途 | OHOS 状态 | 处置 |
|---|---|---|---|
| Qt5Core | 全部目标 REQUIRED | ✅ qt5-qtbase/5.15.2 | 正常依赖 |
| Qt5Qml | scriptabletags 插件 + testscriptabletags（均 QUIET 可选） | ❌ qt5-qtbase 无 Qml 模块 | 插件不构建 + 测试目标不注册（CMake 条件分支自然跳过，豁免） |
| Qt5LinguistTools | testinternationalization（QUIET 可选） | ❌ 未发布 | 测试目标不注册（豁免） |
| Qt5Test | 测试基类 | ✅ qt5-qtbase 含 Test | 测试正常构建 |
| qt5-qtscript | 任务提示核查项 | 不需要——5.3.1 的 scriptabletags 用 QScriptEngine（Qt5Qml），非 QtScript | 无依赖 |

## 上游测试（rule4 全量计数）

上游 BUILD_TESTS=ON 默认形态 `add_test` 注册（两个 grantlee_*_unit_tests
宏的 foreach 循环展开）：

- templates/tests：testsafestring、testbuiltins、testloadertags、
  testdefaulttags、testcachingloader、testfilters、testgenerictypes、
  testgenericcontainers（8 个无条件）+ testscriptabletags（Qt5Qml_FOUND
  条件）+ testinternationalization（LinguistTools_FOUND 条件）
- textdocument/tests：htmlbuildertest、plainmarkupbuildertest（2 个无条件）

**全量 N=12**；适配后可注册 10（Qt5Qml/LinguistTools 未发布 → 2 个条件
目标不注册，CMake 上游逻辑自然处理，无源码修改）。豁免 2 个逐项定性见
test_package/MANIFEST.yml。

## musl 兼容清单

无——grantlee 纯 Qt/C++ 用户态模板引擎，无 glibc 专用 API、无 systemd/
procfs/硬件依赖。

## 已知限制 / 平台说明

- O-1 **scriptabletags 插件缺失**：Qt5Qml 模块未发布（qt5-qtbase 仅
  Core/Network/Gui/Test/Concurrent）。该插件提供 QScriptEngine 驱动的
  脚本化模板标签，OHOS 消费者用 defaulttags/loadertags 等本地标签覆盖
  同等功能。
- O-2 **testinternationalization 不注册**：Qt5LinguistTools（lupdate/
  lrelease 工具链）未发布；i18n 标签本体（i18n.so 插件）不依赖它，
  插件正常构建安装。

## 验证结果

- conan create（ohos-aarch64 profile，--build=missing）：**EXIT-CODE=0**
- **上游测试（ctest 真跑）**：`100% tests passed, 0 tests failed out of 10`
  （templates 8 + textdocument 2；QT_QPA_PLATFORM=minimal——textdocument
  测试用 QApplication，qt5-qtbase 包平台插件仅 minimal/offscreen/vnc）
- test_package（消费者测试）：**5 用例全过**（变量插值/autoescape 转义/
  for 循环/upper 过滤器/未闭合标签受控行为），total failures = 0

## 适配过程与踩坑记录

### 踩坑 1：qt5-qtbase 的 cmake_find_mode=none 消费链

上游 find_package(Qt5Core/Grantlee5) 需要**包内官方 config**——CMakeDeps
不为 cmake_find_mode=none 的包生成 config，也不把其 lib/cmake 加入
CMAKE_PREFIX_PATH。解法（先例 kimageformats5/attica-kf5）：generate() 写
conan_cmakedeps_paths.cmake（conan_toolchain 自动 include）把 qt5-qtbase
与被测包的 lib/cmake 前置，并设 CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON；
grantlee 自身也声明 cmake_find_mode=none（包内上游官方 Grantlee5Config
导出 Grantlee5::Templates target）。

### 踩坑 2：HMDFS 构建产物 .so 重签后才能加载（核心平台知识）

**现象**：test 二进制 rc=127，`Error loading shared library
libGrantlee_Templates.so.5`——el2 目录与 LD_LIBRARY_PATH 均正确仍失败。
**定位**：隔离 dlopen 发现该 .so 报 Permission denied（对比：libkysdk
包内同路径的库可加载）——两者都有 .codesign 段且 display-sign 均显示
self-sign，但 grantlee 的构建产物签名不被本机加载器认可。
**解法**：llvm-objcopy --remove-section=.codesign 删旧段 →
binary-sign-tool sign -selfSign 重签 → chmod 755——重签后 dlopen 立即
成功。test_package 用 setup-el2-runtime.sh 统一布置（拷贝+三段链
实体化+全量重签，幂等哨兵），build() 的上游 ctest 同法
（DRAFT 草稿沉淀为跨包通用知识）。
**注意**：SDK 的 libc++_shared.so 无 .codesign 段且原生签名有效——
重签列表必须排除（objcopy 会失败）。

### 踩坑 3：引擎插件目录布局与编译期宏

GRANTLEE_PLUGIN_PATH 是**编译期宏**（构建机 install 路径），交叉产物
运行时不可达。EnginePrivate::loadCppLibrary 在每个 pluginDir 下拼
`/grantlee/<major>.<minor>/` 查找——插件树须为 `<root>/grantlee/5.3/`，
消费者用 `engine->addPluginPath(root)` 注入（测试程序读
GRANTLEE_TEST_PLUGIN_DIR 环境变量，消费者集成同法，README 有文档）。

### 踩坑 4：textdocument 测试需要平台插件

QApplication 类测试默认找 xcb 平台插件（qt5-qtbase 包仅
minimal/offscreen/vnc）——`QT_QPA_PLATFORM=minimal` 后 2 个测试全过。
