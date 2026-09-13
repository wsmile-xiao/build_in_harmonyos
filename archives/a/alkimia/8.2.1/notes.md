# alkimia 8.2.1 适配笔记

## 基础信息
- 上游: https://invent.kde.org/office/alkimia
- 源码: https://download.kde.org/stable/alkimia/8.2.1/alkimia-8.2.1.tar.xz
- sha256: f921410e180e0a5811e1ee2926954920c6576a72b3b65f53791faa6c85fcb689
- 构建系统: CMake (ECM/KDEInstallDirs)
- 语言: C++ (Qt6/KF6)

## 依赖选型（W0 实测决策记录）
任务背景给的依赖清单（gmp/kconfig/kcoreaddons/ki18n 6.26.0）不完整。上游
CMakeLists Qt6 模式 REQUIRED KF6 组件实为：Codecs、WidgetsAddons、CoreAddons、
Completion、I18n、NewStuffCore/NewStuff(Widgets)、IconThemes、TextWidgets、
XmlGui、Config。制品仓实测：
- ktextwidgets 只有 6.14.0（锁 KF 6.14 系），与 knewstuff 任何已发布版本
  （全系锁 kconfig/6.18 系）构成 conan 版本冲突 → 无法共存。平台任务 #6842
  （ktextwidgets 6.18.0，claimer zxyAtom）已认领未发布，不能等。
- 解法：0001 patch 把 debug 对话框的 KTextEdit 日志窗口降级为 QTextEdit
  （m_logWindow 只调用 setVisible/clear/append，全部是 QTextEdit 原生 API，
  功能等价），并从 find_package/link 中移除 TextWidgets。
- 最终依赖矩阵：qtbase-sql-dbus/6.11.1（Qt6::DBus 变体，akonadi 25.12.3
  先例——基线 qtbase/6.11.1 不带 DBus 组件）、qtdeclarative/6.11.1（qml
  插件）、gmp/6.3.0.1（--enable-cxx 提供 gmpxx，6.3.0 无 C++ 绑定）、
  knewstuff/6.29.0.1、kcompletion/kiconthemes/kxmlgui/kconfigwidgets/
  kguiaddons/kcolorscheme/kitemviews/kconfig/kcoreaddons/ki18n/kcodecs/
  kwidgetsaddons 6.18.0、ecm/6.26.0。
- kxmlgui 的 KF6XmlGuiConfig.cmake find_dependency(KF6ConfigWidgets)，conan
  不传导非 CMakeDeps 依赖 → 显式声明 kconfigwidgets 及其链（akonadi 先例）。

## 关键适配点
1. BUILD_WITH_QT6=ON（QtVersionOption 模块），否则走 Qt4/Qt5 分支报
   FindQt5 找不到。
2. BUILD_APPLETS=OFF（Plasma 未发布）；ENABLE_FINANCEQUOTE=OFF（需 perl）。
3. FindGMP.cmake patch：find gmpxx.h + libgmpxx（alkimia 的 MP_HEADER=gmpxx.h，
   alkvalue 用 mpq_class），同时把 GMPXX_LIBRARIES 并入 GMP_LIBRARIES；
   配方侧 GMP_INCLUDE_DIR/GMP_LIBRARIES 缓存变量直接指向 conan 包。
4. E537/R05 可重定位链接（knewstuff 6.29.0.1 patch 0004 同款）：
   - alkimia 主库 `-Wl,-soname,libalkimia6.so`；测试二进制原相对 NEEDED
     `../bin/libalkimia6.so`（OHOS musl 按 cwd 解析路径型 NEEDED，不查
     LD_LIBRARY_PATH）由 SONAME 后变裸 basename 解决。
   - KF6 依赖（无 DT_SONAME 的已发布包）按裸 -l 基名链接 + PRIVATE
     target_link_directories（ALKIMIA_DEP_LIB_DIRS 注入），链接仍保留
     Qt6::Core/Gui/Widgets/Network/DBus 目标（头文件路径 + SONAME 正常）。
   - package() 后 _make_relocatable 清扫：绝对缓存路径/构建树相对路径
     DT_NEEDED → patchelf 重写为裸 basename（knewstuff 先例）。
5. ctest 运行时 shim：已发布 kconfig/knewstuff 包带 `../../bin/libKF6*`
   相对 NEEDED（它们自己构建树布局的遗留）。OHOS musl 按 cwd 解析 →
   _prepare_ctest_runtime_links 在 build/../bin 建全部依赖库软链。
6. TZ=UTC：testParseQuoteJson（alkonlinequoteprivatetest 内）喂 UTC 日
   边界时间戳，非 UTC 本地时区两条样本落到同一本地日期，map 退化为 1 条
   （上游时区依赖缺陷；实测 TZ=UTC → 9/9 全过）。测试环境注入 TZ=UTC。

## 测试台账（R01）
上游注册测试目标 13 个（BUILD_TESTING=ON 默认形态）：
- ecm_add_tests 批量块 6 个 + 单块 6 个（无 WebEngine 变体）+ appstreamtest
  1 个（appstreamcli 不存在 → 上游 CMake 自动跳过注册，实测 ctest 列出 12）
- 本地实测 ctest 12 项：9 通过 + 3 豁免（离线沙箱无外网）：
  - alkonlinequotestest：fetch https://kmymoney.org/onlinequotestest.php
  - alkdownloadengine-qt-test：真实网络下载
  - alknewstuffenginetest：KNS 引擎访问 https://autoconfig.kde.org/ocs/
    providers.xml，不可达时 SEGFAULT
  - 豁免通过 ctest -E 正则排除（非 adaptation 回归，环境限制）
- alkonlinequoteprivatetest：9 函数 8 过 1 败 → TZ=UTC 后 9/9 过（见上）
- test_package：AlkValue 加法/convertDenominator(GMP mpq)/double 构造路径
  全部实测（输出 "579/100" "579/100" "3/2"），R34 实质 API 调用。

## conan create 结果
RC=0。产物：libalkimia6.so + libqmlalkimia6.so、16 头文件、
LibAlkimia6Config.cmake（Alkimia:: 命名空间）、onlinequoteseditor6 工具。
package_id 6b7c1d6cde4058c65ff7653f2a20abed47f06b0d。

## 平台限制记录
- /tmp 只读（E002）：补丁生成等临时文件走 $TMPDIR。
- 网络：构建/测试环境无外网，网络型测试豁免（见测试台账）。
- OHOS musl 动态加载器：路径型 NEEDED 按 cwd 解析，不走 LD_LIBRARY_PATH。
