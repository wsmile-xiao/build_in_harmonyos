# qtpositioning 5.15.2 适配笔记

## 源码
- 上游从无独立的 qtpositioning tarball：positioning 与 location 同仓发布（qtlocation 仓库），
  源码即 qtlocation-everywhere-src-5.15.2.tar.xz
  - 主源: https://mirrors.tuna.tsinghua.edu.cn/qt/archive/qt/5.15/5.15.2/submodules/qtlocation-everywhere-src-5.15.2.tar.xz
  - 备源: https://download.qt.io/archive/qt/5.15/5.15.2/submodules/qtlocation-everywhere-src-5.15.2.tar.xz
- sha256: 984fcb09e108df49a8dac35d5ce6dffc49caafd2acb1c2f8a5173a6a21f392a0
- 上游 git tag v5.15.2 = commit 02a21217a9706402802f38c646797be8eccb86e4（qtpositioning.git / code.qt.io）

## 模块结构（qmake 系，与 qtdeclarative/qtgraphicaleffects/qqc2 同族）
- 仓库根 qtlocation.pro = load(qt_parts)（会连带构建 location，不可直接用）
- 本包范围内构建单元与顺序（对应上游 src/src.pro 的 SUBDIRS 依赖链截取）：
  1. src/3rdparty/clipper → libqt_clipper.a（静态助手库）
  2. src/3rdparty/poly2tri → libqt_poly2tri.a
  3. src/3rdparty/clip2tri → libqt_clip2tri.a（依赖上面两个）
  4. src/positioning → libQt5Positioning.so（QGeoCoordinate/QGeoShape 家族/
     QGeoPositionInfo(+Source)/QGeoAreaMonitorSource/QNmeaPositionInfoSource）
  5. src/positioningquick → libQt5PositioningQuick.so（QML 类型 C++ 侧）
  6. src/imports/positioning → qml/QtPositioning/libdeclarative_positioning.so（QML 插件）
  7. src/plugins/position/positionpoll → plugins/position/libqtposition_positionpoll.so
     （QGeoAreaMonitorSource 插件，"positionpoll" key）
- 出范围（不构建）：location 模块、geoclue/geoclue2（需 dbus）、gypsy、serialnmea
  （需 serialport）、winrt 等平台来源插件——平台范围内均无依赖可用

## 构建方式（复用 qt5-qtquickcontrols2/5.15.2 成熟模式）
- 逐子项目 qmake -spec linux-clang + make -jN QMAKE_STRIP=""；每步之间补齐 .so 别名副本
- 依赖: qt5-qtbase/5.15.2.2（qmake/Qt5Core/Gui）+ qt5-qtdeclarative/5.15.2（Qml/Quick 私有头）
- _fix_qtbase_paths（qt.conf 重写 + 50 个 .pri 重定位）+ _fix_qtdecl_paths
  （62 个 .pri 合并进 qtbase mkspecs）与 qqc2 完全同款

## 关键适配点
1. **单子项目 qmake 无 configure 产物**：src/plugins/position/position.pro 的
   `QT_FOR_CONFIG += positioning-private` + `qtConfig(gypsy)` 在无顶层 configure 时
   报 "Could not find feature gypsy"。解法：直接对 positionpoll 子目录跑
   positionpoll.pro（本就是范围内唯一可建插件，geoclue/gypsy/serialnmea 条件
   依赖均不满足）。
2. **syncqt 转发头修复（含版本目录）**：include/QtPositioning 与
   include/QtPositioningQuick 下是 syncqt 生成的转发头
   （#include "../../src/positioning/xxx.h"），包搬迁后失效 →
   build() 尾部 _sync_forward_headers() 用 src/ 下真头覆盖（公共头 + 5.15.2/
   版本化私有头目录，两份模块都处理）。
3. **OHOS 禁符号链接（ln EPERM）**：qmake 对 libQt5Positioning 等生成的
   .so/.so.5/.so.5.15 别名链在 -j 并行下竞态失败（Error 1 (ignored)，make 仍
   RC=0）。解法：_materialize_shared_object_links() 在每步 make 后用文件副本
   补齐别名（Qt5Positioning/PositioningQuick 各 3 个）。后续定位与 QML 插件的
   链接阶段依赖这些别名。
4. **positionpoll 工厂语义（消费者须知）**：插件经 QGeoPositionInfoSourceFactory
   接口暴露，areaMonitor() 仅在 QGeoAreaMonitorPolling::isValid()（= 默认
   positionInfoSource() 非空，见 qgeoareamonitor_polling.h:75）时返回实例。
   平台范围内无默认定位源插件（serialnmea 需 serialport、geoclue 需 dbus），
   因此 createSource("positionpoll") 返回空属预期行为；插件可用性以
   availableSources() 枚举 + QPluginLoader 直载 + 工厂接口 cast 验证。
5. **QNmeaPositionInfoSource 解析要求**（5.15 源码实证）：
   - 解析器强制 NMEA XOR 校验和（qlocationutils.cpp: hasValidNmeaChecksum，
     无 '*' 段一律判 invalid）
   - SimulationMode 首条修复要求含完整日期时间的语句（GPRMC/GNRMC，ZDA 亦可）
   - 仿真回放：首条修复立即发出，后续语句按 NMEA 时间戳差用定时器回放
     （实测 1 秒间隔准点发出第二条）
   - GGA 高度 → coordinate().altitude()；GGA HDOP → HorizontalAccuracy；
     RMC 速度 → GroundSpeed 属性（knots × 1.852/3.6，qlocationutils.cpp:211）
6. **QML 导入路径**：与 qqc2 同——QCoreApplication::addLibraryPath() 不扩展
   QML 引擎 importPathList，须 engine.addImportPath()（或 QML_IMPORT_PATH 环境变量，
   test_package 两者都设）。QV4_FORCE_INTERPRETER=1 + QML_DISABLE_DISK_CACHE=1
   （OHOS W^X 拦 JIT）在 test_package 环境内固化。
7. **QGeoPath::length 闭合语义（真机实测）**：length(indexFrom, indexTo) 在
   indexTo 取默认值 -1 时 wrap=true，会补上末点→首点的闭合段
   （qgeopath.cpp:551-567；实测三顶点路径 length() 48875.9 ≈ 2× 开放长度 24438，
   精确含闭合段）；开放折线长度须显式 length(0, size()-1)。
8. **QGeoPolygon 两种包含语义（真机实测 + 源码实证）**：containsCoordinate()
   为周长元素匹配（QGeoPolygonPrivate 继承 QGeoPathPrivate::containsCoordinate
   = m_path.indexOf()，qgeopath.cpp:582）；点是否落在多边形内须用
   QGeoShape::contains()（QGeoPolygonPrivate::polygonContains →
   clip2tri::pointInPolygon，qgeopolygon.cpp:606），两者互不等价。

## 上游测试（tests/auto 定位子集）
- 全树测试文件（git tag v5.15.2 递归）：tests 树 85 个 .pro、67 个 tst_*.cpp、
  tests/auto 45 个 .qml（其中 10 个为数据文件）——定位子集 21 个 tst_*.cpp，
  location 侧 46 个
- 注册可执行测试目标 N=20：doublevectors、positionplugintest、qgeoaddress、
  qgeoareamonitor、qgeocircle、qgeocoordinate、qgeolocation、qgeopath、qgeopolygon、
  qgeopositioninfo、qgeopositioninfosource、qgeorectangle、qgeosatelliteinfo、
  qgeosatelliteinfosource、qgeoshape（15 个独立目标）+ qnmeapositioninfosource 目录
  5 个（realtime、simulation、realtime_generic、simulation_generic 及夹具自测
  tst_dummynmeapositioninfosource；该目录第 6 个 tst_*.cpp 为多目标共享源码）；
  夹具插件 positionplugin/positionpluginV1 为辅助件不计入
- 出范围（未执行）：declarative_geoshape 的 QML 测试（tests/auto/declarative_geoshape，
  被测 QtPositioning QML 单例实现于本包），其 .qml 含上游遗留
  `import QtLocation 5.5`——QtLocation 属 location 模块不在本包交付物内，运行期
  import 无法解析（未修改上游文件）
- 测试减少说明：定位子集 20 个可执行目标 100% 实跑、无裁剪；location 侧 46 个
  tst_*.cpp 与 34 个 QML 测试文件需 QtLocation 模块（及网络服务），不在本包
  交付物内未构建
- 真机执行：QT_QPA_PLATFORM=offscreen + QV4_FORCE_INTERPRETER=1 +
  QML_DISABLE_DISK_CACHE=1，逐测试独立进程
- **实测（2026-10-04 真机，两轮独立执行结果一致）：20/20 目标 rc=0，
  1434 passed / 0 failed / 24 skipped（= 100%）；24 项 QSKIP 全部来自
  tst_qgeosatelliteinfosource 的 DefaultSourceTest（平台无默认卫星源插件）**

## test_package（消费者测试，执行器式）
- CMake find_package(Qt5Positioning) + Qt5::Positioning/Qt5::Core/Qt5::Qml
- 五用例（TEST PASS/FAIL + SUMMARY，任一失败 exit 1，共 38 项检查）：
  1. coordinate_math——QGeoCoordinate 实测距离/方位/atDistanceAndAzimuth 往返
     一致性 + 1° 纬度 ≈ 111 km 绝对值锚定
  2. shape_algorithms——QGeoPath 开放长度 length(0, size-1) 与默认 wrap 长度
     双语义、QGeoRectangle 包含/相交、QGeoPolygon 点包含
     （QGeoShape::contains，clipper 静态库运行期验证）与周长元素匹配
     （containsCoordinate）双语义
  3. nmea_simulation——真实 NMEA 语句流（GGA+RMC × 2 秒）经
     QNmeaPositionInfoSource SimulationMode 回放，验证坐标/高度/速度/时间戳
     与逐条推进时序
  4. positionpoll_plugin——availableSources() 枚举 + QPluginLoader 直载
     plugins/position/libqtposition_positionpoll.so + 工厂接口 cast +
     插件元数据 Keys/Monitor
  5. qml_positioning——QQmlEngine import QtPositioning 5.15，PositionSource
     属性读写 + CoordinateAnimation 实例化
- **实测（2026-10-04 真机）：5/5 测试用例通过、38/38 项检查 PASS
  （conan create 的 test_package 阶段与独立执行器两种方式均 rc=0）**
