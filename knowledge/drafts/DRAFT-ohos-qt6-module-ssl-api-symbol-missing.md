# DRAFT-ohos-qt6-module-ssl-api-symbol-missing — Qt 子模块基于非 SSL qtbase 编译时不导出 SSL API 符号，TLS 消费者链接报 undefined symbol

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-08
> **Severity**: 🟡 medium | **Category**: ohos / linking / dependency / conan / cmake

## 相关既有条目（同族差异化定位）

本 skill 与既有 "qtbase FEATURE 开关" 及 "Qt6 子模块消费" 条目共享 Qt 适配背景，但本条目是 **子模块已编译、仅 SSL API 符号不导出（链接期 undefined symbol），修法为同源码新建依赖契约变体**——非重复条目；申报路径 B 时以此差异化定位为准。

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **E323**（Qt6DBus 不可消费：qtbase FEATURE_dbus=OFF → 组件缺失、find_package 失败） | 正式收录 | qtbase 配方功能开关关闭导致 **Qt 组件整体缺失、配置期不可消费**（无 libQt6DBus.so、无 Qt6DBusConfig.cmake） | 同族（都是 qtbase FEATURE 开关影响下游 Qt 模块），但**问题面不同**——E323 是**组件整体缺失（配置期 find_package 失败）**，本条目是**组件已编译但 API 符号不导出（链接期 undefined symbol）**；修法也不同——E323 是**改配方开 FEATURE_dbus + 补依赖 + package_info 补组件**，本条目是**不改模块源码/原配方、同源码新建 .1.1.1 依赖契约变体** |
| **E438**（Qt6 子模块复用 qtbase 的 Qt6Config 与 harmonyos-clang mkspec） | 正式收录 | 子模块构建期 CMake find 配置（Qt6_DIR/mkspec） | 非本题——那是**构建期 CMake 配置复用**，本条目是**链接期符号缺失**，与 find 配置无关 |
| **E439**（qt5compat 依赖声明） | 正式收录 | Qt 模块依赖声明 | 非本题——那是**依赖声明**（requires 传导），本条目是**依赖契约错配导致符号不导出** |
| **DRAFT-qtscxml-6.11.1-qt6-submodule-cmake-find**（Qt6 子模块 cmake find 模式） | 草稿 | 子模块 Qt6Scxml/StateMachine 的 CMake find 路径与 Qt6Config 遮蔽 | 非本题——那是**cmake find 模式/路径**，本条目是 **FEATURE 开关决定的符号裁剪**（链接期），问题层完全不同 |
| **E520**（libQt6ShaderTools Error relocating / LD_LIBRARY_PATH） | 正式收录 | 子模块运行期动态库加载路径 | 非本题——那是**运行期加载路径**，本条目是**构建期符号裁剪导致的链接期缺失** |

> 全库查证（2026-09-08）：`QWebSocket` / `ignoreSslErrors` / `sslErrors` / `setSslConfiguration` / `QT_CONFIG(ssl)` / `FEATURE_openssl` 命中 0 条——无正面撞车；本条目为真增量。

## Scope（何时用）

在 OHOS（或其他 Qt 依赖链）上构建基于 qtbase 的 Qt 6 子模块、且下游要走 TLS（wss:// / QSslSocket / QWebSocket SSL API）时，若出现：

- 消费者**编译通过、最终链接失败**，报 `ld.lld: error: undefined symbol: QWebSocket::*`（SSL 相关成员）；
- 已确认所依赖的 qtbase 为**非 SSL 变体**（`QT_CONFIG(ssl)=off`，FEATURE_openssl=OFF）；
- 目标模块的 SSL API 是绕不开的真需求（如 eID 客户端强制 wss://）。

典型实例：ausweisapp/2.5.4（`ConnectRequest.cpp` / `RemoteWebSocketServerImpl.cpp` 调用 QWebSocket SSL API）。

## Symptom

```text
ld.lld: error: undefined symbol: QWebSocket::sslConfiguration() const
ld.lld: error: undefined symbol: QWebSocket::ignoreSslErrors(QList<QSslError> const&)
ld.lld: error: undefined symbol: QWebSocket::setSslConfiguration(QSslConfiguration const&)
ld.lld: error: undefined symbol: QWebSocket::preSharedKeyAuthenticationRequired(QSslPreSharedKeyAuthenticator*)
ld.lld: error: undefined symbol: QWebSocket::sslErrors(QList<QSslError> const&)
clang: error: linker command failed with exit code 1
# 编译 100% 通过，最终链接（cmake --build 收尾）失败
```

## Root Cause

1. Qt 6 子模块（qtwebsockets 等）在 **configure/编译期按所依赖 qtbase 报告的 feature 开关裁剪 API**；
2. 非 SSL qtbase（`FEATURE_openssl=OFF` → `QT_CONFIG(ssl)=off`）下，`QWebSocket` 的 SSL 相关成员函数（`ignoreSslErrors` / `setSslConfiguration` / `sslErrors` / `preSharedKeyAuthenticationRequired` / `sslConfiguration`）**整体不编译进 libQt6WebSockets.so**——头文件声明仍在（上游源码未动），但动态库无符号可解析；
3. 消费者用 `find_package(Qt6 WebSockets)` + 链接 `Qt6::WebSockets` 编译期一切正常（头文件齐全），**最终链接才暴露符号缺失**；
4. 依赖链上 qtwebsockets 配方写死依赖非 SSL 的 `qtbase/6.11.1`，即使应用侧 override 了 SSL 变体 qtbase，qtwebsockets 也不会同步重建 → 需要依赖侧新建对应变体。

## Recommended Solution

**主方案：依赖契约变体（同源码、不同依赖契约）。**

1. qtbase 侧已有 SSL 变体（`qtbase/6.11.1.1.1`，FEATURE_openssl=ON + openssl/3.5.6.1）；
2. qtwebsockets 复制原 6.11.1 配方为 `6.11.1.1.1`：**同一上游源码归档（SHA-256 不变）**，仅 `requirements` 改为依赖 `qtbase/6.11.1.1.1`，`generate()`/`validate()` 对齐 SSL 变体契约（QT_QMAKE_TARGET_MKSPEC=harmonyos-clang、QT_BUILD_TESTS=True 等）；
3. 顶层 manifest 不更新（与 qtbase 变体引入时一致）；原 `6.11.1` 配方不动，非 SSL 用途不受影响；
4. 消费者的 `override=True` 与 `requires` 指向 `qtwebsockets/6.11.1.1.1` 即可拿到带 SSL 符号的制品。

```python
# qtwebsockets/6.11.1.1.1 conanfile.py requirements
def requirements(self):
    self.requires("qtbase/6.11.1.1.1")
```

验证：`nm -D libQt6WebSockets.so | grep ignoreSslErrors` 应能查到导出的 SSL 符号；`conan create` + consumer 最终链接通过。

**回退方案**：直接改 qtbase/6.11.1 把 FEATURE_openssl 打开——会改变既有 6.11.1 制品依赖契约（引入 openssl 依赖），影响所有下游非 SSL 用途，不推荐。

## 单库实证

| 库 | 角色 | 结果 |
|----|------|------|
| **ausweisapp/2.5.4** | 触发方（PR #7912 构建 #41146） | ❌ 覆盖前：最终链接 src/AusweisApp 报 5 个 QWebSocket SSL 符号 undefined（qtwebsockets/6.11.1 旧制品） |
| **qtwebsockets/6.11.1.1.1** | 修复载体（PR #8845） | ⏳ 新建 SSL 变体（依赖 qtbase/6.11.1.1.1），CI 构建验证中 |
| **qtbase/6.11.1.1.1** | 前置变体 | ✅ 既有 SSL 变体（FEATURE_openssl=ON） |

## 测试覆盖边界

- 本条目修复对象是 **符号导出**（链接期），验证以 `nm -D` 符号清单 + consumer 最终链接成功为准；
- 上游测试声明口径见 PR #8845：上游 qtwebsockets 6.11.1 源码 tests/auto 共 11 个测试目标（9 单元含 6 个私有守卫 + 1 集成 + 1 QML 守卫），适配后注册运行 4 个（3 公开单元 + 1 CMake 集成），6 个私有目标因 qtbase `QT_FEATURE_private_tests=OFF` 未注册、1 个 QML 目标因无 Qt Quick 未注册，另新增 1 个鸿蒙特有 consumer 测试；
- 变体方案不改模块源码，上游测试源码与测试目标保持原样。
