# libsignon-qt

`libsignon-qt` 是 [signond](https://gitlab.com/accounts-sso/signond)（Single Sign On daemon）的 Qt 客户端库，
提供在线账号凭据的存储与 SSO 认证 API（`SignOn::AuthService` / `SignOn::AuthSession` / `SignOn::Identity` / `SignOn::IdentityInfo` 等）。

- 上游仓库: https://gitlab.com/accounts-sso/signond
- 上游版本: 8.61（tag `VERSION_8.61`，2022-03-09）
- 许可证: LGPL-2.1-or-later
- 构建系统: 上游为 **qmake**（`lib/SignOn/libsignon-qt.pri`）；本适配包经 `exports_sources` 自带 `CMakeLists.txt`，按 **CMake + Qt6** 构建

## 鸿蒙 PC 适配要点

1. **qmake → CMake 包装**：上游只发 Qt5 形态（`TARGET=signon-qt5`、`CMAKE_BASENAME=SignOnQt5`），
   且 ohpcd 的 `qtbase` 包未提供 OHOS mkspec，无法直接 qmake 交叉编译。
   本包自写 `CMakeLists.txt`（Qt6 形态：目标 `signon-qt6`、CMake 包 `SignOnQt6`），随配方分发。
2. **Qt6 定位**：ohpcd `qtbase` 的根 `cpp_info` 为 `cmake_find_mode=none`，CMakeDeps 不生成 Qt6 config；
   配方 `generate()` 显式把 `<qtbase>/lib/cmake/Qt6` 写入 `Qt6_DIR` 缓存变量。
   消费侧同样需先 `find_package(Qt6 CONFIG)`（见 `8.61/test_package/`）。
3. **头文件布局**：`lib/SignOn` 内部以 `<SignOn/xxx.h>` 互相包含（`.pri`: `INCLUDEPATH += . ..`），
   构建期 include 根为 `lib/`，安装期为 `include/signon-qt6`；
   `AuthService`/`AuthSession`/`Error`/`Identity`/`IdentityInfo`/`SecurityContext`/`SessionData`
   是无扩展名转发头，按 `install(FILES)` 安装。
4. **范围**：只构建客户端库（`lib/SignOn`）；`server/`（signond 守护进程）与 `src/`（插件）不在本包内。
5. **无补丁**、仅依赖 `qtbase/6.11.1.1`，默认静态构建（`-o libsignon-qt/*:shared=True` 可切共享库）。

## 产物

| 产物 | 路径 |
|---|---|
| 库 | `lib/libsignon-qt6.a`（静态；shared 时为 `.so`） |
| 公开头 | `include/signon-qt6/SignOn/*.h` 与 7 个无扩展名转发头 |
| CMake 包 | `lib/cmake/SignOnQt6/{SignOnQt6Config.cmake,SignOnQt6Targets.cmake,…}` |
| pkg-config | `lib/pkgconfig/libsignon-qt6.pc` |

## 消费方式

```cmake
find_package(Qt6 COMPONENTS Core DBus CONFIG REQUIRED)   # 需 Qt6_DIR 指向 qtbase 包内 lib/cmake/Qt6
find_package(SignOnQt6 REQUIRED 8.55)                    # CMakeDeps/Auto 均可
target_link_libraries(<target> SignOnQt6::SignOnQt6 Qt6::DBus)
```

```cpp
#include <SignOn/Identity>      // 转发头
#include <SignOn/IdentityInfo>
```

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 8.61 | published | 首次适配；conan-verify 8 门禁通过，W3 本地 CI 通过 |
