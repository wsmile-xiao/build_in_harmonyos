# DRAFT: KF6 托盘 StatusNotifierItem 同名双配方选型与 Qt6DBus 单提供者基座

- **来源**：ktimer 26.04.0 适配（KDE release-service 26.04.0，2026-09-30）
- **状态**：草稿（待知识库主编审核）
- **判重范围**：平台知识图谱 / 本仓 `knowledge/` / `经验文档` / 同批草稿（四范围）

## 现象（无报错的静默降级）

ktimer 的 `CMakeLists.txt` 需要系统托盘与会话总线：

```cmake
find_package(KF6 ${KF_MIN_VERSION} REQUIRED COMPONENTS ... DBusAddons ...)
find_package(KF6StatusNotifierItem ${KF_MIN_VERSION} REQUIRED)
target_link_libraries(ktimer KF6::DBusAddons KF6::StatusNotifierItem ...)
```

制品仓里同时存在两份**同上游、同版本、同产物**的配方：

| 配方 | 目录 | 关键开关 | 依赖基座 |
|------|------|----------|----------|
| `statusnotifieritem/6.26.0` | `archives/s/` | `USE_DBUS=ON`（DBus adaptor + libdbusmenu-qt 导出器为核心功能） | `qtbase/6.11.1.1`、`kwindowsystem/6.18.0` |
| `kstatusnotifieritem/6.26.0` | `archives/k/` | `USE_DBUS=OFF`（"headless OHOS baseline"） | `qtbase/6.11.1`、`kwindowsystem/6.26.0` |

两者的安装产物都是 `libKF6StatusNotifierItem.so` 与
`KF6StatusNotifierItemConfig.cmake` ⇒ **`find_package` 与链接都不会失败**，
但选错时 `org.kde.StatusNotifierItem` / `org.kde.StatusNotifierWatcher` /
`org.freedesktop.Notifications` 三个 DBus 适配器被上游 `#if HAVE_DBUS`
守卫整段编译掉 ⇒ 托盘在 OHOS 上静默失效，**没有任何构建期报错**。

## 根因

1. 制品仓按包名首字母分目录，`kstatusnotifieritem` 与 `statusnotifieritem`
   版本号、上游 URL、产物名全部相同，只能靠**配方 docstring** 区分；
2. KDE 上游把 DBus 适配器做成可编译开关，关闭后仍能完整构建 —— 失效只在
   运行期表现为"托盘不出现"，属于典型的"编译通过 ≠ 适配完成"（R40）；
3. Qt6 侧同构：`qtbase/6.11.1` 是 `FEATURE_dbus=OFF`，`qtbase/6.11.1.1` 是
   `FEATURE_dbus=ON`（自带 `Qt6::DBus` 组件），两版只差一个修订号。

## 方案

**KF6 托盘 / DBus 消费者选型三步：**

1. **读 docstring，不看版本号**：打开
   `archives/<首字母>/<包名>/<版本>/conanfile.py`，逐条核对
   `USE_DBUS` / `FEATURE_dbus` / 依赖基座；
2. **要托盘协议就选 `statusnotifieritem/6.26.0`（`archives/s/`，USE_DBUS=ON）**；
   要 `Qt6::DBus` 就选 `qtbase/6.11.1.1`（FEATURE_dbus=ON），
   让整张图只有**一个 Qt6 提供者**，不必再引入 `qtbase-sql-dbus` 变体；
3. **交叉核对依赖基座**：`statusnotifieritem/6.26.0` 拉 `kwindowsystem/6.18.0`，
   与 `kio/6.14.0` 内部的 6.14 钉版冲突时，用消费者 `override=True`
   把整张图统一到 6.18 闭包（`ktuberling/26.04.0` 同款）。

最终配方（ktimer 26.04.0）：

```python
self.requires("qtbase/6.11.1.1", override=True)   # Qt6 Core/Widgets/DBus 单提供者
self.requires("kdbusaddons/6.29.0")                # KDBusService → Qt6DBus
self.requires("statusnotifieritem/6.26.0")         # USE_DBUS=ON 托盘
self.requires("kio/6.14.0")
self.requires("kconfigwidgets/6.18.0")
for dep in ("kconfig", "kcoreaddons", "karchive", "kservice", "kcolorscheme",
            "kguiaddons", "kitemviews", "kjobwidgets", "kwindowsystem",
            "kauth", "solid", "kbookmarks", "kcompletion", "kiconthemes",
            "kcodecs"):
    self.requires(f"{dep}/6.18.0", override=True)  # 抬到 6.18 闭包
self.tool_requires("extra-cmake-modules/6.29.0")
```

## 验证

```bash
conan create archives/k/ktimer/26.04.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

- 选对时：`conan graph info` 图可解（无 qtbase 版本冲突），`conan create` 通过，
  `test_package` 的 `ktimer --version`（`QT_QPA_PLATFORM=offscreen`）冒烟 PASS；
- 选错时：**构建同样通过**，只有运行期托盘不出现 —— 因此本条目的抓手是
  选型期的 docstring 核对，不是失败日志。

## 适用范围 / 反例

- **适用**：任何 `find_package(KF6StatusNotifierItem)` 的 KDE 托盘应用；
  任何需要 `Qt6::DBus` 的 KF6 应用（`KDBusService` / `KNotification` /
  StatusNotifierItem）；制品仓存在"同名近似双配方"时的通用选型流程。
- **反例 / 解除条件**：纯 headless、不需要系统托盘与会话总线的库，
  选 `kstatusnotifieritem/6.26.0`（USE_DBUS=OFF）反而更轻（少拉
  `kwindowsystem` 与 `Qt6DBus`）—— 判据是"消费者是否要托盘协议或会话总线"，
  不是"一律选 ON"。
- **风险**：`qtbase/6.11.1.1` 与 `qtbase-sql-dbus/6.11.1` 若同时入图
  （如经 `kauth/6.18.0` 传递），会存在两个 Qt6 提供者；两者产物互为超集，
  但应尽量用 `override=True` 把 `qtbase` 收敛到单一提供者。

## 查重与新增价值

- **平台知识图谱**：`E323`（改 qtbase 配方开 `FEATURE_dbus`）、`E441`（新建
  `qtbase-sql-dbus` 变体）、`E542`（Qt6LinguistTools provider 配方）
  —— 都是"**改造/新建配方**"路径；本条目是"**已有两份配方时如何选**"，
  不改任何框架配方，解法不同。
- **同批草稿**：`DRAFT-E5xx-ohos-qtbase-dual-ecosystem-kf6-version-gate` 讲
  qtbase 双生态**版本冲突**与 KF6 版本闸补丁；本条目讲的是**不报错**的
  `USE_DBUS` 静默降级与 docstring 选型流程，触发签名与处置动作都不同。
- **新增价值**：把"编译通过 ≠ 适配完成（R40）"落到一个可执行的选型检查项，
  覆盖 `kmousetool` 之外尚未被记录的 KDE 托盘类应用。

## 关键词

`statusnotifieritem`、`kstatusnotifieritem`、`KF6StatusNotifierItem`、
`KStatusNotifierItem`、`USE_DBUS`、`FEATURE_dbus`、`qtbase/6.11.1.1`、
`Qt6::DBus`、`KDBusService`、托盘、system tray、双配方、静默降级
