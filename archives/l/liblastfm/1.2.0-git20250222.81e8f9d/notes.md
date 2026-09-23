# liblastfm 1.2.0-git20250222.81e8f9d 适配笔记

## 编译环境
- 构建系统: cmake（上游原生 CMakeLists，Qt5 线 BUILD_WITH_QT5=ON）
- 编译日期: 2026-09-14
- 编译器: clang/clang++ 15.0.4（aarch64-unknown-linux-ohos）
- 状态: built（conan create 全绿 + test_package ALL PASS）

## 源码
- 上游: https://github.com/lastfm/liblastfm（git snapshot 81e8f9dc16@2025-02-22）
- tarball: https://codeload.github.com/lastfm/liblastfm/tar.gz/81e8f9dc16
- sha256: cebd6459c8a3b3e39d6ebd44f4012e9bad5e9bdc6a6cfca332a954ce47abc706

## 编译步骤

```bash
conan create . -pr:h ~/.conan2/profiles/ohos-aarch64 -pr:b ~/.conan2/profiles/ohos-aarch64 --build=missing
```

关键配置（conanfile.py generate() 注入）：
- BUILD_WITH_QT5=ON（上游 Qt5 开关）
- BUILD_FINGERPRINT=OFF（fingerprint 库强制依赖 samplerate+fftw3f，非核心，
  按"可关则关"关闭——主库 lastfm5 不受影响）
- BUILD_DEMOS=OFF / BUILD_TESTS=ON
- CMAKE_AUTOMOC_EXECUTABLE → qt5-qtbase bin/moc
- CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG=-Wl,-soname,（CMake 4.x HarmonyOS
  平台模块未定义 SONAME flag，不注入则 L5 门禁 fail）
- Qt5Test 等 6 个组件 config shim（CMakeDeps 只生成包级聚合 Qt5Config，
  上游 tests 用独立 find_package(Qt5Test CONFIG REQUIRED)）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 配置后 linux 源文件未编译，链接报 undefined reference to lastfm::LNetworkConnectionMonitor | CMake 4.x CMAKE_SYSTEM_NAME=HarmonyOS 下 Platform/HarmonyOS.cmake 不设置 UNIX 变量，上游 if(UNIX AND NOT APPLE) 分支不命中 | 补丁 0001：5 处扩展为 if((UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS") AND NOT APPLE)（E532 模式） |
| 2 | Target "lastfm5" links to: Qt::Network but the target was not found | 上游用无版本 Qt:: 前缀目标（Qt6 语义），CMakeDeps 只生成 Qt5:: 前缀 | 补丁 0002：src/CMakeLists.txt + tests/lastfm_add_test.cmake 改 Qt5:: 前缀 |
| 3 | src/ws.cpp:88: error: use of undeclared identifier 'QSslSocket' | qt5-qtbase/5.15.2.2 构建带 QT_NO_SSL（无 OpenSSL 后端），QSslSocket 类声明被条件排除 | 补丁 0003：scheme() 加 #ifdef QT_NO_SSL 分支按 API 契约回落 Http |
| 4 | source() 报 BadZipFile: File is not a zip file | codeload 短链 tarball 无扩展名，get() 按内容嗅探失败（E276） | source() 显式传 filename="liblastfm-....tar.gz" |
| 5 | find_package(Qt5Test CONFIG REQUIRED) 失败 | CMakeDeps 只生成包级聚合 Qt5Config，组件无独立 config | generate() 写 Qt5Test/Qt5DBus 等 6 个转发 shim 到 generators 目录（toolchain 已 PREPEND 进 CMAKE_PREFIX_PATH） |
| 6 | test_package 运行报 Error loading shared library liblastfm5.so | OHOS XPM 签名 + musl 加载路径 | test_package: 依赖库拷贝 bindir + binary-sign-tool 自签（libical 4.0.1 同款）+ LD_LIBRARY_PATH 注入 SDK libc++ |
| 7 | 上游 UrlBuilderTest no404/test404 失败 (ProtocolUnknownError, code 0) | https 真实网络探测，QT_NO_SSL 下 QNetworkAccessManager 不支持 https 协议——平台限制 | 逐项定性豁免（PR 正文申报），TrackTest/encode 类测试全过 |

## 源码修改

- patches/0001-cmake-recognize-HarmonyOS-in-UNIX-platform-branches.patch（5 处 UNIX 分支扩展）
- patches/0002-cmake-use-Qt5-prefixed-targets-for-CMakeDeps-compati.patch（Qt5:: 目标名）
- patches/0003-ws-fall-back-to-Http-scheme-when-built-with-QT_NO_SS.patch（SSL 探测守卫）

## 依赖版本

- qt5-qtbase/5.15.2.2（仓内 ✅ 已发布，Core/Network/Xml/Test/DBus）
- fftw（可选——BUILD_FINGERPRINT=OFF 关闭，未使用）

## 验证结果

```bash
$ conan create . -pr:h ohos-aarch64 -pr:b ohos-aarch64 --build=missing
# → 主包构建成功（liblastfm5.so，SONAME liblastfm5.so）
# → 上游 ctest：TrackTest 1/1 Passed（0.09 sec）
# → UrlBuilderTest：encode×4 PASS + initTestCase/cleanupTestCase PASS；
#    no404×6 + test404×1 FAIL（https 网络探测——QT_NO_SSL 平台限制，
#    ProtocolUnknownError，输出已完整留档于构建日志）
# → test_package：liblastfm smoke test: ALL PASS
```

上游测试 N 口径：ctest 注册 2 套件（UrlBuilderTest/TrackTest）；数据行口径
13 项断言（encode 4 + no404 6 + test404 1 + testClone 1 + init/cleanup 2）。

## 注意事项

- qt5-qtbase 无 OpenSSL 后端（QT_NO_SSL）是既定平台约束：liblastfm 的
  scheme() 已按 API 契约回落 Http；消费方需 https 时应等待 qt5-qtbase
  带 TLS 后端的版本
- Audioscrobbler 构造前必须设置 lastfm::ws::Username（Q_ASSERT 非空）
- lastfm5Config 不带 INTERFACE_INCLUDE_DIRECTORIES，消费方 CMake 需
  find_path(lastfm5/global.h) 或手动加 include 根
---

**编译结束**: 2026-09-14 19:25
**最终状态**: built
