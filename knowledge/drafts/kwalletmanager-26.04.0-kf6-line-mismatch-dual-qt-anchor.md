# KF6 版本线错位依赖的选线决策树与 Qt6 双锚点共存方案

## 错误特征

KDE Gear/KF6 应用适配时出现以下任一现象：

1. `ERROR: Version conflict: Conflict between kXXX/6.19.0 and kXXX/6.18.0 in the graph`
2. `Cannot load recipe ... Required by 'kYYY/6.18.0'`（配方缓存连锁损坏）
3. conan create 阶段全部 KF6 依赖退化为源码编译（`--build=missing` 触发全链重建，单包 30 分钟+）
4. CI worker 上 KF6 依赖的上游测试套超时失败（全链重建的连带后果）
5. `Duplicated requirement: karchive/6.18.0`（override 写法错误）

## 根因（平台机制因果）

ohpcd 制品仓的 KF6 包按**代际线**发布：6.14/6.18/6.26 各自锚定一代 qtbase
与互为 binary closure 的 KF6 邻居。conan 的 package_id 由完整依赖闭包哈希
决定——任一依赖换线，全部 KF6 包 package_id 变化，远端 prebuilt binary 全部
失配，`--build=missing` 退化为全链源码重建。

KDE Gear 应用常同时依赖多代组件：kwallet 仅 6.18 线、kio 仅 6.14/6.26 线、
kcmutils/kstatusnotifieritem 仅 6.26 线。Qt6 侧还有双变体陷阱：
qtbase/6.11.1 是 FEATURE_dbus=OFF（无 Qt6::DBus/qdbusxml2cpp），
qtbase-sql-dbus/6.11.1 才带完整 DBus——D-Bus 系应用 find_package(Qt6 ...
DBus) 必须锚后者。

## 三步决策树（kwalletmanager 26.04.0 实证）

### 1. 选线

找出"不可替代"依赖的唯一在档线（本例 kwallet/6.18.0 仅 6.18 在档），整图
锚定该线；全部直接 requires 精确对齐。选线前用 `conan list "pkg/*" -r=ohpcd`
枚举每个依赖的完整版本谱系。

### 2. 不共线的可选依赖 trim（kgoldrunner 先例）

逐点分析使用量，优先走等价替换：

- KIO 5 处本地文件调用（storedGet/storedPut/CommandLauncherJob）→ QFile /
  QProcess::startDetached 等价替换（补丁 + CMake find_package 摘除）
- KCM 模块 + KAuth helper → 上游自带 `ENABLE_KAUTH=OFF` 开关整目录跳过
- 托盘图标（kstatusnotifieritem）→ find_package 降 OPTIONAL_COMPONENTS +
  `#ifndef KWM_TRIM_SNI` 守卫（#else 保留上游完整行为），未找到时窗口模式

**关键坑**：trim 掉的依赖原靠其传递性补齐的间接依赖（KF6::ItemViews /
KF6::Codecs / KF6::Service）会在 CMake Generate/编译期报
"target not found" / "KService file not found"——必须在 find_package 与
target_link_libraries 显式补回。

### 3. Qt6 双锚点共存（kio-kwallet 先例）

**不要 force 对齐 Qt**（libkgapi 式 force=qtbase/6.11.1.2 是弯路：改全部
KF6 package_id → binary 全失配 → 全链源码重建 → 测试套沙箱超时）。正确做法：

- 直接 `self.requires("qtbase-sql-dbus/6.11.1")`（与核心依赖 kwallet 同锚）
- 其余 KF6 6.18 保持自然锚 qtbase/6.11.1，**两包共存一图**，不改任何
  package_id，binary 全量复用
- 仅在手工 `conan_cmakedeps_paths.cmake` 里把 qtbase-sql-dbus 前缀放最前，
  使其 Qt6Config.cmake（含 DBus 模块 + qdbusxml2cpp）在 find_package 胜出

### 附加：karchive override

kiconthemes/6.18.0 新 revision 要求 karchive/6.19.0 与其余 6.18 包冲突时：
`self.requires("karchive/6.18.0", override=True)`——**只写一次**（与直接
requires 并存会报 Duplicated requirement）。

## 降级方案

- 依赖无法 trim（核心功能依赖不共线包）→ 按拓扑序先适配发布缺线依赖
  （R36），或等官方补发 binary
- 双锚点在某闭包失配 → 再评估 force 整图对齐（代价=全链源码重建，需 CI
  预算可容纳且上游测试套沙箱可跑）

## 红线

- ❌ 禁止 conan remove 后不重下导致配方缓存半损坏（"Cannot load recipe"
  连锁报错，逐个 conan remove + conan download 修复）
- ❌ 禁止混线硬凑（binary 层必然失配，configure 阶段才爆，浪费 30 分钟+）
- ❌ override 行与直接 requires 行不得并存同名同版本

## 验证

- 本机 conan create（ohos-aarch64 profile）：package
  66e66ca3ac3e146d1b0639a7ec49f8e40f784b49，test_package 6/6 PASS
- CI #66456：passed（PR #14240）
- 证据链：archives/k/kwalletmanager/26.04.0/{conanfile.py, patches/,
  notes.md}；先例 archives/k/kgoldrunner/26.04.0、archives/k/kio-kwallet/
  6.28.0；反例 archives/l/libkgapi/26.04.0
