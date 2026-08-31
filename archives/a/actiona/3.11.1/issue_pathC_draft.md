# 高难度挑战 Issue 提交模版（路径 C）— actiona 3.11.1

【申请人账号】your_account
【队伍名称】队伍名
【申请日期】2026/08/15
【库名称】actiona

## 关联 PR

- PR：!xxxx（待提交，一库一 PR）
- PR 链接：https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/xxxx
- 分支信息：feat/actiona-3.11.1 → main
- 当前状态：open（待提交）
- 当前路径：路径 A（基础适配）+ 路径 B（贡献创新）+ 路径 C 候选

## 申请事项

本 Issue 的目的：**不是直接申请路径 C 分值，而是请求评审委员会确认 actiona 3.11.1 是否纳入路径 C 候选清单**。actiona 是跨 Qt / OpenCV / X.Org 三大生态的自动化脚本执行引擎，本次适配暴露并解决了制品仓系统性缺失依赖链与多个鸿蒙平台特定编译问题。若证据不足，本 PR 仍按路径 A + 路径 B 推进。

## 高难度分析

**总起**：actiona 不是普通"编译一次通过"的适配，而是系统性/跨阶段的复杂问题——依赖链跨三大生态、制品仓缺失整套 X.Org 运行库与 libnotify、且存在多个鸿蒙平台特有的宏污染与头文件链问题，每次全量编译 30-60 分钟、需 40+ 次验证迭代。

### 1. 依赖链系统性缺失（跨生态发布）

- Qt6 全组件依赖（Qml/Network/Sql/Widgets/Core5Compat/DBus/Multimedia/MultimediaWidgets/TextToSpeech/LinguistTools）。
- **X.Org 运行库链缺失**：libXtst→libXi→libXfixes 制品仓全缺，需从零发布（参照 libXext 先例，含 libtool `.la` 校验绕过、ABI 版本映射、package_info 显式依赖声明）。
- **libnotify 缺失**：notifyinstance.cpp 依赖 `<libnotify/notify.h>`，需从零搭建 meson 配方（含 AR 注入、glib pkg-config 变量修复、test_package 鸿蒙动态库限制处理）。

### 2. 鸿蒙平台特定编译问题（非标准 Linux 行为）

- **QT_NO_DBUS / QT_NO_OPENSSL 宏污染**：qtbase（非变体）qconfig.h 定义 `QT_NO_DBUS=1`/`QT_NO_OPENSSL`，导致 QtDBus 头文件走 dummy 分支（`Q_DBUS_EXPORT` 未定义）、QxtSmtp 的 `connectToSecureHost` 声明被跳过——需调整 QtCore 依赖指向 qtbase-sql-dbus 变体 + 构建期临时注释宏定义（try/finally 恢复）。
- **XInput.h 缺失**：libxtst 的 XTest.h include XInput.h，头文件链需在配方中补齐。
- **动态库运行时限制**：鸿蒙 musl 动态链接器使用 namespace 配置，忽略 LD_LIBRARY_PATH，test_package 运行时验证策略需适配。

### 3. 子模块缺失与构建体系混合

- qtjsapi（ExternalProject 独立 CMake 进程）、QDarkStyleSheet、mINI 为上游 git 子模块（tarball 不含），需单独补下载并注入 Qt6 配置。
- 混合构建体系（CMake + ExternalProject + meson + autotools），需逐个适配。

## 已完成的证据材料

1. Qt 层依赖链发布（6 包）：qtcore5compat / qtmultimedia / qttexttospeech / qttools / qtbase-sql-dbus / qtdeclarative（含 qtbase-sql-dbus 变体提供 Qt6DBus）。
2. X.Org 依赖链发布（3 包）：libxfixes / libxi / libxtst（conan-verify + finish 通过）。
3. libnotify 发布（1 包）：meson 配方从零搭建，conan-verify 通过。
4. actiona 配方修复（40+ 次验证迭代）：QT6::QmlPrivate、qtjsapi ExternalProject、lrelease、X11 头文件链、libxcb 版本冲突、QT_NO_DBUS/QT_NO_OPENSSL 宏处理、XInput.h/mINI/libnotify 补下载等。

## 当前状态与边界

- PR 当前状态：待提交（一库一 PR，所有库全部完成后统一提交）。
- CI 状态：actiona conan-verify 编译推进至 75%+（历史最高，所有已知阻塞已解决，剩余为 libnotify 制品仓解析与收尾验证）。
- 内容边界：本 Issue **仅申请路径 C 候选确认，不宣称已满足分值**。

## 建议验收项

1. 验收 actiona 3.11.1 全量编译通过（conan-verify 全部 G 门禁 PASS + finish W3 本地 CI 通过率）。
2. 验收依赖链完整性：X.Org 三件套 + libnotify 已发布至制品仓，actiona 可正常解析。
3. 验收鸿蒙平台特定问题均已解决并有配方内证据（QT_NO_* 宏处理、XInput.h/mINI/libnotify 补下载）。

## 申请边界

| 路径 | 分值 | 说明 |
|------|------|------|
| 路径 A | [x] 分候选 | 基础适配申请 |
| 路径 B | 10 分候选 | 适配困难库分析报告（验证方法可复用：libtool .la 绕过、宏污染处理等） |
| 路径 C | 仅申请候选确认 | 不直接声明分值 |
| 其他 | 不单独申报 | — |

最终以评审委员会审核结果为准。

## 需要评审委员会确认的问题

1. 是否认可 actiona 3.11.1 作为路径 C 高难度挑战候选。
2. 路径 C 的最低验收证据是什么。
3. 鸿蒙平台特有的宏污染（QT_NO_DBUS/QT_NO_OPENSSL）与依赖链系统性缺失，是否计入高难度评分维度。
4. 若当前暂不纳入路径 C，是否认可本 PR 先按路径 A + 路径 B 继续评审。
