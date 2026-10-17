# DRAFT-ohos-qt-ssl-feature-missing：Qt 基座未启用 SSL → QSslSocket/QSslCipher 未声明

> Contributor: SnowTT | Status: Draft | Updated: 2026-09-06
> Source: ausweisapp 2.5.4 HarmonyOS PC adaptation（PR #7912）
> 对应：knowledge/drafts/DRAFT-ohos-qt-ssl-feature-missing.kv

## 现象

Qt6 应用在 OHOS 上配置/编译阶段报 Qt SSL 类未声明：

```text
/storage/.../b/cmake/tests/openssl.cpp:41:6:
  error: use of undeclared identifier 'QSslSocket'
      if (QSslSocket::sslLibraryVersionString() != QLatin1String(OpenSSL_version(OPENSSL_VERSION)))
          ^
/storage/.../b/cmake/tests/openssl.cpp:50:13:
  error: use of undeclared identifier 'QSslCipher'
                                  return !QSslCipher(pCipherName).isNull();
                                          ^
2 errors generated.
```

AusweisApp 2.5.4 的上游 `cmake/Libraries.cmake` 在 `if(LINUX OR BSD)`
分支用 `try_run(... cmake/tests/openssl.cpp ...)` 校验 Qt 的
`QSslSocket` 是否与链接的 OpenSSL 版本兼容，该测试编译即失败 →
`message(FATAL_ERROR "Your OpenSSL library looks incompatible")`，
CMake configure 中止，`conan create` 失败（CI `conan-build-test` 0/1）。

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条目增量（差异化） |
|----------|----------|--------|----------------------|
| E323 | graph | qtbase 缺 DBus 组件 → 下游 `find_package(Qt6DBus)` 组件缺失 | **包发现层**（CMake find_package 找不到组件）|
| E441 | graph | qtbase 缺 Sql 组件 → 下游 `find_package(Qt6Sql)` 组件缺失 | **包发现层**（CMake find_package 找不到组件）|
| 本条目 | draft | qtbase 缺 **SSL** 功能（`FEATURE_openssl=OFF`）→ 下游编译期 `QSslSocket/QSslCipher` 未声明 | **编译期 API 层**：类整体不声明（`QT_NO_SSL`），错误形态为 `use of undeclared identifier`，且上游 OpenSSL 兼容性 `try_run` 在 configure 期直接拦停 |

与 E323/E441 同族（均为 qtbase 基座功能组件缺失导致下游失败），但问题层
不同：E323/E441 是 find_package 组件发现失败（链接前包发现），本条是 Qt
SSL API 编译期缺失（SSl 特性未编译进 QtNetwork），错误形态、诊断路径、
修法（改用 SSL 变体 + override 全图）均不同。

## Root Cause

Qt6 的 `QSslSocket`/`QSslCipher`/`QSslError`/`QSslConfiguration` 仅在
Qt 基座构建时启用 SSL 特性（`FEATURE_openssl=ON`，即未定义 `QT_NO_SSL`）
才会被声明。OHOS 适配的 qtbase 基座若以 `FEATURE_openssl=OFF` 构建，则：

1. `QtNetwork` 头文件里 SSL 相关类整体缺失；
2. 下游任何使用 Qt SSL API 的应用编译期即报 `use of undeclared identifier`；
3. 上游若在 configure 期用 `try_run` 编译 `openssl.cpp` 做 OpenSSL 兼容性
   校验，则该测试编译失败 → configure 直接 `FATAL_ERROR`。

错误表象是"编译失败"，易被误判为 include 路径/头文件缺失问题，实际根因
是**依赖的 qtbase 基座没开 SSL**，而非应用自身代码问题。

## Recommended Solution

1. **主方案**：把下游配方对 qtbase 的依赖改为带 SSL 支持的变体，并用
   `override=True` 强制整个依赖图统一：

   ```python
   def requirements(self):
       # Qt6 base with OpenSSL support (harmonyos SSL variant)
       self.requires(
           "qtbase/6.11.1.1.1",     # FEATURE_openssl=ON + requires openssl
           override=True,
           transitive_headers=True,
           transitive_libs=True,
       )
   ```

   注意：qtdeclarative/qtwebsockets/qtsvg 等模块按 plain `6.11.1` 基座构建，
   必须用 `override` 让它们统一解析到 SSL 变体，否则下游仍拿到无 SSL 的基座。

2. **回退方案**：若 registry 无现成 SSL 变体，给 qtbase 配方加
   `FEATURE_openssl=ON` 并 `requires("openssl/3.5.6.1")`，重新构建发布后
   再让下游依赖（改动基座配方需先过 L0j 版本门禁）。

## 单库实证

| 库 | 角色 | 结果 |
|----|------|------|
| ausweisapp/2.5.4 | 依赖 qtbase/6.11.1.1（无 SSL） | `conan create` 失败：OpenSSL 兼容性 try_run 编译报 QSslSocket/QSslCipher 未声明 |
| ausweisapp/2.5.4 | 依赖 qtbase/6.11.1.1.1（SSL 变体，override 全图） | OpenSSL 兼容性测试编译通过，configure 不再 FATAL_ERROR（后续 PCSC/LINUX 修复见 PR） |

## 测试覆盖边界

- 覆盖：OpenSSL 兼容性 `try_run`（openssl.cpp）编译/链接通过；Qt SSL 类
  声明可见（无 `QT_NO_SSL`）。
- 未覆盖：运行期 TLS 握手（需真机 + 服务端），本条只保证编译期 SSL API
  可用与基座 SSL 特性开启。
