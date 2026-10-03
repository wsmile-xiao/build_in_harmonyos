# D-Bus 依赖的 Qt/KDE 库适配 OHOS 双要点：qtbase 变体选型 + 无 dbus-daemon 环境的消费者测试

> Draft: `DRAFT-KUNIFIEDPUSH-2604-DBUS-LESS-CONSUMER`
> Stem: `kunifiedpush-26.04.0-dbus-less-consumer-test` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-KUNIFIEDPUSH-2604-DBUS-LESS-CONSUMER
- **来源**: kunifiedpush 26.04.0 适配（PR !14214，commit b173497f80，CI 构建 #66384 全绿）
- **类别**: ohos-platform|testing|build-system
- **触发工具**: conan|cmake|ctest
- **阶段**: configuration|runtime

## 错误特征

两类症状，分别出现在 configure 期与 test_package 运行期：

**症状一（configure 期，qtbase 选型错）**：被适配库 CMakeLists 里
`find_package(Qt6 COMPONENTS DBus)` / `target_link_libraries(... Qt6::DBus)`
报 `Target "xxx" links to: Qt6::DBus but the target was not found`。
原因是制品仓 KF6 6.26 基线所用的 `qtbase/6.11.1` 是缩减面包：
`FEATURE_dbus=OFF`、`FEATURE_openssl=OFF`、testlib 关闭，
qtbase 又声明 `cmake_find_mode=none`，Qt6DBus 的 CMake config 根本不在包里。

**症状二（运行期，bus-less 主机）**：test_package 消费者二进制直接段错误
`Test #1: test_xxx (SEGFAULT)`，且无任何 Qt 日志前置。栈顶是
`QDBusConnection::sessionBus().interface()->registeredServiceNames()`——
OHOS 无会话 dbus-daemon，sessionBus 连接上的 `interface()` 返回 nullptr。

实际观测（2026-10-01，OHOS aarch64，clang 15，qtbase-sql-dbus/6.11.1）：

| 测试路径 | 结果 |
|----------|------|
| 非 serviceName 构造 Connector（上游构造函数无条件探测总线） | SEGFAULT |
| 空 serviceName 构造（上游提前 return 分支） | Passed 0.08s |

## 根因

1. **qtbase 变体分裂**：仓内 `qtbase/6.11.1`（KF6 基线）刻意关掉了
   DBus/openssl/testlib 走精简面；需要这些组件的件必须换
   `qtbase-sql-dbus/6.11.1`（Core/Network/Gui/Widgets/Xml/Sql/DBus/Test，
   附 `bin/qdbusxml2cpp` host 工具与 `lib/cmake/Qt6DBus/Qt6DBusMacros.cmake`，
   akonadi 25.12.3 / alligator 26.04.0 先例）。版本号相同不代表能力面相同。
2. **总线在线探测在 bus-less 主机不可用**：KDE 的 D-Bus 客户端库普遍在
   构造/初始化时无条件调 `sessionBus().interface()->...` 列举服务名做
   distributor/service 发现——这是"库本身正常、消费者测试崩"的典型形态。

## 修复方案（可复制）

**(1) W0 选型规则**：适配前先 grep 候选 qtbase 配方的 FEATURE 开关再定
requires：需要 `Qt6::DBus`/`Qt6::Test`/`Qt6::Sql` → `qtbase-sql-dbus/6.11.1`；
纯 Core/Gui → `qtbase/6.11.1`。不要看 KF6 先例的版本号直接抄。

**(2) ECM 件接线**（kcrash 6.26.0 模式）：
`ECM_MODULE_PATH` 手动指向 ecm 包 `share/ECM` 的
modules/find-modules/kde-modules；qtbase 系 `cmake_find_mode=none` 时手写
`conan_cmakedeps_paths.cmake`，把每个依赖的 `lib/cmake`、包根、`include`
前缀进 CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH 并
`set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)`。

**(3) bus-less 安全消费者测试**：读上游源码找提前返回分支。
kunifiedpush `Connector` 对空 serviceName 在
`loadState()/selectDistributor()` 之前 return（仅 qCWarning）——
既保住 D-Bus adaptor 注册路径（总线缺失时上游降级为 warning），
又能真调全部属性 API（state/endpoint/vapid round-trip）。

**(4) C++ most-vexing-parse 陷阱**：`Connector connector(QString())`
会被解析成函数声明，后续全部成员访问报
"member reference base type ... is not a structure or union"。
用命名变量 `const QString s; Connector c(s);` 规避。

## 降级方案

无法换 qtbase 变体（版本被钉死在缩减包）时：给被适配库打 patch 按
ANDROID 分支裁掉 DBus 路径（上游通常有 Q_OS_ANDROID 守卫的替代实现）；
或测试运行期起 `dbus-daemon --session --fork` 供连接；
或 LD_PRELOAD/打桩拦截 `interface()`。优先选上游已有的提前返回分支。

## 验证证据

- 本机 `conan create`：上游 CTest 2/2（connectorutilstest 0.07s +
  contentencryptiontest 0.11s），test_package 1/1（0.08s）。
- CI 构建 #66384（OpenHarmonyPCDeveloper-CI-034）：L0/L1 门禁 + conan
  test_package 全部通过。
- 包 reference：
  `kunifiedpush/26.04.0#8f36382d6d1353a5a50a7cf41b200117:4e974afdcfff02f7afe621f2325ad52a59453305`。

## 红线

- 不得把"编译/打包成功"当作 D-Bus 类库可用性证据——必须跑真实消费者
  二进制（本例第一版 test_package 就是在 SEGFAULT 才暴露选型问题）。
- 上游测试裁剪必须用上游官方开关（本例 `KUNIFIEDPUSH_CLIENT_ONLY=ON`，
  与上游 Android 交付同范围），并在 PR 统计表写明裁剪原因与缺件存证。
