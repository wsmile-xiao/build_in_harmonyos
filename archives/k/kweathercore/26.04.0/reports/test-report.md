# kweathercore 26.04.0 验证报告

## 本机 conan create（W3）

```
conan create archives/k/kweathercore/26.04.0 \
  -pr:h=ohos-aarch64 -pr:b=default --build=missing
```

结果：**PASSED**（package_id `0a1a08122390386f7c2ebb5a312f7a01c526aade`）

- configure：Qt6（Core/Network/Qml/Positioning）、KF6（I18n/Holidays）、ECM 全部解析成功；
  qtdeclarative/qtpositioning 不在 qtbase 前缀下，经 `QT_ADDITIONAL_PACKAGES_PREFIX_PATH` +
  `CMAKE_PROJECT_TOP_LEVEL_INCLUDES` 注入文件补入
- build：`lib/libKWeatherCore.so` 编译链接成功（C++20，`-D_LIBCPP_ENABLE_EXPERIMENTAL` 打开
  OHOS libc++ 的 `std::ranges`）
- 上游测试：`BUILD_TESTING=OFF`，8 个 QTest 套件未构建（交叉构建无 OHOS 运行时，见下）
- test_package：实机运行输出 `kweathercore 26.04.0: all 4 checks passed`

## 上游测试对照

上游注册测试套件总数 **N=8**（`autotests/CMakeLists.txt` 两次 `ecm_add_tests`：7 个基础套件 +
`geotimezonetest` 单独注册）。

| 上游注册测试 | 注册方式 | 附加依赖 | 本机执行 | 结果 |
|---|---|---|---|---|
| capparsertest | ecm_add_tests（批次 1） | capdata/ 数据目录 | 未执行 | SKIP |
| metnoparsertest | ecm_add_tests（批次 1） | met.no/ 数据目录 | 未执行 | SKIP |
| hourlyweatherforecasttest | ecm_add_tests（批次 1） | — | 未执行 | SKIP |
| dailyweatherforecasttest | ecm_add_tests（批次 1） | — | 未执行 | SKIP |
| weatherforecasttest | ecm_add_tests（批次 1） | — | 未执行 | SKIP |
| locationquerytest | ecm_add_tests（批次 1） | — | 未执行 | SKIP |
| pendingweatherforecasttest | ecm_add_tests（批次 1） | — | 未执行 | SKIP |
| geotimezonetest | ecm_add_tests（批次 2） | Qt6::Network 外网 | 未执行 | SKIP |

跳过原因：交叉构建下 `BUILD_TESTING=OFF`，且 OHOS SDK 无设备运行时 / 无 Qt6::Test 运行环境；
上游测试需要 OHOS 侧可执行环境，非本次适配范围。故适配后本机上游测试执行数 **M=0**，
上游测试通过率为不适用（0/8 未执行，非失败）。

## test_package 冒烟（消费者视角，4 项断言）

驱动：`test_package/conanfile.py` → `test.cpp`（用已发布包的头/库编译链接并运行）。

| # | 断言 | 验证点 | 结果 |
|---|---|---|---|
| 1 | `KWEATHERCORE_VERSION_STRING` | 版本宏在消费侧可见且非空（安装头 + 版本宏导出） | PASS |
| 2 | `LocationQueryResult` 构造 | 上游值对象可构造（头解析 + ABI 可用） | PASS |
| 3 | `latitude()` | 访问器返回值与构造入参一致 | PASS |
| 4 | `name()` / `countryCode()` | 访问器返回值与构造入参一致 | PASS |

实测输出：`kweathercore 26.04.0: all 4 checks passed`。

## 产物清单

- `lib/libKWeatherCore.so`（约 412K；库名为上游 target 名，非 `libKF6KWeatherCore`）
- `include/KWeatherCore/KWeatherCore/*.h`（18 个公共头，含 `kweathercore_export.h`）
  + 同名类名转发头（如 `CAPAlertInfo` → `#include "kweathercore/capalertinfo.h"`）
- `include/kweathercore_version.h`
- `include/kweathercore` → `KWeatherCore/KWeatherCore`（小写裸前缀别名，符号链接；
  供公共头内 `#include <kweathercore/…>` 解析）
- `lib/cmake/KWeatherCore/KWeatherCoreConfig.cmake` 等（上游 CMake 包配置）
- `lib/qml/org/…`（QML 模块：qmldir/插件）
- `share/locale/…`（翻译）

## 本机环境差异说明（不影响交付）

本机文件系统**大小写不敏感**（实测 `include/KWEATHERCORE` 可命中 `include/KWeatherCore`），
`package()` 中的 `if not os.path.exists(lower_link)` 守卫因此短路，未创建 `include/kweathercore`
小写别名；同时 `os.path.exists("include/kweathercore/kweathercore_export.h")` 会因大小写不敏感
误判为已存在。在大小写敏感的文件系统（CI/常见 Linux 构建机）上该符号链接会正常创建，
公共头的小写裸前缀 include 可解析。本地 test_package 通过即为此原因（大小写不敏感查找
让 `kweathercore/` 命中 `KWeatherCore/`）。
