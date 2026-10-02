# DRAFT-qlog-0.51.1-qtwebengine-hard-dep-blocks-adaptation

## 结论

qlog 0.51.1 无法在 ohpcd 依赖条件下适配，唯一阻断点是 **qtwebengine**：
qmake 工程 `QLog.pro:7` 无条件 `QT += ... webenginewidgets`，源码 19 处
`QWebEngine*` 无 `#ifdef` 守卫；制品仓 `conan list "qtwebengine/*" -r=ohpcd`
返回 `Found 0 pkg/version recipes`，仓库 `archives/` 亦无 qtwebengine 目录。
按 SKILL 判定表 → `dependency_missing`（换一个有该配方的制品仓即可解决，
非本机环境问题，故不是 `env_unsupported`）。

## 关键判断：为什么不去掉 WebEngine 再适配

- 移除 WebEngine = 删除地图功能（`ui/WebEnginePage.*`、`ui/OnlineMapWidget.*`
  及 `MainWindow`/`MapPageController`/`QSODetailDialog`/`StatisticsWidget`
  的地图交互），属于 **R40 禁止的功能删除/空壳 stub**，会制造欺骗性交付物。
- QtWebEngine 内嵌完整 Chromium（V8/Blink/沙箱 + node/gn/ninja 依赖链），
  移植量级与「单包适配」不同，不属本任务范围；应作为独立 Qt 模块适配任务
  （与 qtbase/qtdeclarative 同级的 qt6 子模块 recipe）推进。
- 判据记录：**依赖缺口必须上报，不得靠改上游功能绕过**（PF4 依赖闸 +
  本任务的用户约束一致）。

## 依赖盘点（可直接复用，避免二次盘点）

已发布可用：qtbase / qtcharts / qtwebsockets / qtserialport / qtdeclarative /
qtwebchannel / qtmultimedia / qt5compat **6.11.1**、qtkeychain **0.14.2**、
sqlite3 **3.53.4**、openssl **3.5.8.1**、zlib **1.3.1**；
缺失：**qtwebengine（阻断点）**；
hamlib：本任务已单独适配（`archives/h/hamlib/4.7.1/`，分支 `feat/hamlib-4.7.1`），
合并后该行转为可用。

## 预判的后续适配点（qtwebengine 就绪后）

- `QLog.pro:545` 用 `pkg-config --modversion hamlib` 探测版本 → OHOS 上需让
  Conan 包提供 pkg-config 文件，或改用 `HAMLIBINCLUDEPATH`/`HAMLIBLIBPATH`；
- `PKGCONFIG += openssl`（`QLog.pro:626`）同理；
- `QLog.pro:654` 回退引用 `$$[QT_INSTALL_PREFIX]/../Src/qtbase/src/3rdparty/sqlite`
  在 Conan 场景不存在 → 需改走 `sqlite3` 依赖；
- Qt6 `dbus`/`printsupport` 模块在 OHOS 的实际可用性需实测。

## 验证

```bash
conan list "qtwebengine/*" -r=ohpcd
# -> Found 0 pkg/version recipes matching qtwebengine/* in ohpcd
grep -n "^QT" QLog.pro
# -> 7:QT += core gui sql network xml charts webenginewidgets serialport dbus quickwidgets webchannel websockets printsupport
grep -rn "QWebEngine" --include="*.cpp" --include="*.h" . | wc -l
# -> 19
```

## 相关

- 触发实例：qlog/0.51.1（2026-09-28）
- 关联产物：`archives/h/hamlib/4.7.1/`（依赖项适配）、
  `/storage/Users/currentUser/鸿蒙PC/PR正文/pr_qlog_0.51.1.md`（无法适配报告）
