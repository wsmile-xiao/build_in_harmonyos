# kcodecs5 5.116.0 适配笔记

> KDE Frameworks 5（KF5/Qt5）版 kcodecs 库（libKF5Codecs.so），与已有的
> kcodecs/6.26.0（KF6/Qt6）归档分开。参考配方：
> - **kcoreaddons5/5.116.0**（同 KF5/Qt5、5.116.0 基线，Qt5 依赖写法、
>   KF_IGNORE_PLATFORM_CHECK、CMAKE_SYSTEM_NAME、ECM_MODULE_PATH、
>   conan_cmakedeps_paths.cmake、Qt mkspecs 兼容）
> - **kcodecs/6.26.0**（同库 KF6 版，补丁思路与 CTest 测试配置）

## 编译环境
- 构建系统: cmake（ECM 6.20.0）
- 编译日期: 2026-09-25
- 编译器: clang/clang++ 15.0.4（OHOS toolchain）
- 平台: HarmonyOS PC arm64（ohos-aarch64 profile）
- 状态: built → conan-verify PASS → finish published

## 依赖版本

- **qt5-qtbase/5.15.2**（Qt5Core，制品仓已发布；conan download --only-recipe 已验证）
  - 传递依赖：zlib/1.3.1
- **ecm/6.20.0**（tool_requires，ECM，制品仓已发布）

## 源码

`https://download.kde.org/stable/frameworks/5.116/kcodecs-5.116.0.tar.xz`（R39 官方源）
SHA256: `a489d22e91cafcb60854c6e914969e1f3f8270b403baf2ec3a1d76ae2bd3680e`

## 关键适配点

| # | 适配项 | 做法 | 原因 |
|---|--------|------|------|
| 1 | `KF_IGNORE_PLATFORM_CHECK=TRUE` | tc.variables | OHOS 不在 KDE 平台白名单，configure 直接 FATAL |
| 2 | `CMAKE_SYSTEM_NAME=Linux` | tc.variables | CMake 4.1 无 Platform/HarmonyOS，UNIX 变量不成立；OHOS 是 POSIX 系，强制 Linux 平台语义（R32 安全：全程无 `__OHOS__` 宏） |
| 3 | `KDE_INSTALL_USE_QT_SYS_PATHS=OFF` | tc.variables | 安装到 kcodecs5 自己的 prefix，不污染 Qt5 sys 路径 |
| 4 | `ecm_install_po_files_as_qm(poqm)` 禁用 | `patches/0001-CMakeLists.txt.patch` | 需要 Qt5LinguistTools，制品仓未发布（与 kcoreaddons5 0001 同一补丁思路） |
| 5 | `ECM_MODULE_PATH` 手动设置 | generate() | CMakeDeps 生成的 ECMConfig.cmake 不传播该变量，而项目 `set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH})` 依赖它 |
| 6 | `conan_cmakedeps_paths.cmake` 手动生成 | generate() | qtbase 用 cmake_find_mode=none，CMakeDeps 不把其 lib/cmake 加入 CMAKE_PREFIX_PATH |
| 7 | Qt mkspecs 兼容 | `_prepare_qt_mkspec_compat()` | Qt5CoreConfigExtrasMkspecDir.cmake 引用 `${prefix}/../b/mkspecs/linux-clang`，conan 包布局下不存在，复制 p/mkspecs → b/mkspecs |
| 8 | `BUILD_TESTING=ON` | tc.variables | 配置上游 autotests（7 项 ctest），探索阶段全部运行通过 |
| 9 | `BUILD_QCH=OFF` | tc.variables | 不生成 API 文档 |
| 10 | 补丁仅 OHOS 应用 | `if self.settings.os == "OHOS"` | Linux 原生构建不受影响 |

## 与 kcodecs/6.26.0（KF6）适配的差异（如实记录）

1. **不需要 libiconv fallback**（与 KF6 相反，关键差异）：
   - KF6（Qt6）走 `QStringDecoder`，OHOS qtbase 未编 ICU → 无法解码
     RFC2047 legacy charset，kf6 补丁 0002/0003 加了 iconv fallback。
   - **KF5（Qt5）走 `QTextCodec`**（src/kcodecs.cpp:319-326
     `KCharsets::charsets()->d->codecForName(...)`），Qt5Core 自带 legacy
     charset 实现，**不依赖 ICU**，因此 OHOS 上 `rfc2047test` 也直接通过，
     无需引入 libiconv 依赖和 fallback 补丁。
2. **不需要 C++20 相关补丁**：5.116.0 的 src/CMakeLists.txt 显式
   `CXX_STANDARD 14`（gperf 3.1 兼容原因），没有 KF6 6.26.0 的
   `std::span`/`<=>` 问题，故 KF6 的 0004/0005 补丁不适用。
3. **R32 平台判断**：配方全程不判断 `settings.os == "Linux"` 之外的窄条件；
   OHOS 分支用 `str(self.settings.os) == "OHOS"`，并保留
   `in ("Linux", "OHOS")` 兼容语义的默认路径（Linux 原生走无补丁路径）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 失败 `Could not find Qt5LinguistToolsConfig.cmake`（ECMPoQmTools.cmake:153 → ecm_install_po_files_as_qm） | qt5-qtbase 包不含 LinguistTools，制品仓未发布 qt5-linguisttools | patches/0001 注释掉 `ecm_install_po_files_as_qm(poqm)`（同 kcoreaddons5 0001） |
| 2 | configure 提示 `System is unknown to cmake, create Platform/HarmonyOS` | CMake 4.1 无 HarmonyOS platform module | `CMAKE_SYSTEM_NAME=Linux`（E092 已知风险，配方已处理） |
| 3 | `System is unknown to cmake, create Platform/HarmonyOS`（test_package configure 阶段） | 同上 | test_package 侧不依赖 UNIX 语义，仅 find_package KF5Codecs/Qt5Core，configure 正常通过（warning 级） |
| 4 | conan create test_package 执行二进制失败：`Error loading shared library libKF5Codecs.so.5`（rc=127） | OHOS 沙箱的动态加载器忽略 LD_LIBRARY_PATH，用户路径二进制无法解析 Conan 包内 .so（kcoreaddons5 同款环境限制，非打包缺陷） | test() 增加两层策略：能运行就实际执行（真机路径）；沙箱不可执行时回退 **link-level proof**：`readelf -d` 断言 NEEDED `libKF5Codecs.so.5` + `nm -u` 断言 `base64Encode`/`quotedPrintableEncode`/`decodeRFC2047String` 符号已解析 |
| 5 | 首次 conan-verify G2 FAIL：link-level proof 误报缺 `_ZN7KCodecs18quotedPrintableEncode` | 期望符号的 mangled 长度前缀写错（实际 `_ZN7KCodecs21quotedPrintableEncodeERK10QByteArrayb` / `_ZN7KCodecs19decodeRFC2047StringERK7QString`） | 改用 demangled 稳定子串匹配（与 kcoreaddons5 `_verify_links` 同款写法），修复后 G2 PASS |

## 验证结果

### 探索性编译（手工 cmake，OHOS 真机）
- configure ✓ / `make -j4` 100% ✓ / `make install DESTDIR` ✓
- 产物：`libKF5Codecs.so.5.116.0` + `libKF5Codecs.so.5` → `libKF5Codecs.so`
  + `include/KF5/KCodecs/*.h`（KCodecs/KCharsets/KEncodingProber/KEmailAddress/
  kcodecs_version.h/kcodecs_export.h）
- `lib/cmake/KF5Codecs/`：KF5CodecsConfig.cmake / ConfigVersion.cmake /
  Targets.cmake / Targets-release.cmake
- **ctest 7/7 全部通过**（详见 reports/test-report.md）

### conan create（W3 本地验证）
- **PASS**，G0-G4 + L2/L4/L5 全部通过（reports/conan-verify-report.md）
- test_package 消费者测试：沙箱不可执行 → link-level proof 通过

## 产物
- `libKF5Codecs.so.5.116.0`（SONAME `libKF5Codecs.so.5`）
- 纯库包，**无命令行工具**，不需要 commands.json（R38）

## 注意事项

- init-build 与 conan-init 都把构建系统误判为 autotools（kcodecs5 是纯
  CMake + ECM 项目），需手工改用 CMake 配方（参考 kcoreaddons5 5.116.0 改写）。
- Gperf 3.1 来自系统 `/data/service/hnp/bin/gperf`，CI 侧同样具备。
  上游注释说明 gperf < 3.1 会为函数参数加 `register` 关键字（C++14 起非法），
  本环境 gperf 3.1 无此问题，**若 CI gperf 降级需重新评估 CXX_STANDARD 14 设置**。
- 平台差异一律在 CMake 层处理（CMAKE_SYSTEM_NAME=Linux、
  KF_IGNORE_PLATFORM_CHECK），源码/补丁中**无 `__OHOS__` 宏**（R8/PF5）。
- `cpp_info` 采用 `cmake_find_mode=none` + `builddirs=lib/cmake` + `libs=[KF5Codecs]`，
  让安装的 KF5CodecsConfig.cmake 自己驱动 `find_dependency(Qt5Core)`。
---

**编译结束**: 2026-09-25 22:22
**最终状态**: published
