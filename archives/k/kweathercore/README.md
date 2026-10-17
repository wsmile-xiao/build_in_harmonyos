# kweathercore

KDE 天气核心库（KDE Gear 26.04.0，Qt6/KF6）。

## 描述

上游形态为 KWeatherCore 共享库，提供地理位置查询（Geo URI 解析、
LocationQueryResult 值对象）、 sunrise/set 计算、天气预告解析
（CAP v1.1 alert 格式）与时区/坐标工具。无独立可执行文件，交付
`libKWeatherCore.so` 及公共头文件，供 KDE 天气类应用链接使用。

## 已编译版本

- 26.04.0 (2026-09-25)

## 特性

- 地理位置查询与 LocationQueryResult 解析
- 日出/日落时间计算
- CAP v1.1 天气警报（CAPAlertInfo）解析
- 时区与坐标工具（KWeatherCore/kweathercore_version.h 版本宏）

## 使用方法

```cmake
find_package(KWeatherCore REQUIRED)
target_link_libraries(app KF6::KWeatherCore)
```

Conan 包：`kweathercore/26.04.0`（package_id
`0a1a08122390386f7c2ebb5a312f7a01c526aade`，配方见 `26.04.0/conanfile.py`）。

## 适配说明

- 交叉构建 `BUILD_TESTING=OFF`，上游 8 个 QTest 套件未执行；
  test_package 以消费者视角冒烟验证（4 项断言）。
- C++20 兼容：OHOS libc++ 需 `-D_LIBCPP_ENABLE_EXPERIMENTAL`
  才可用 `std::ranges::any_of`（见 notes.md 问题表 #1）。
- 上游测试与验证明细：`26.04.0/reports/test-report.md`、
  `26.04.0/test_package/MANIFEST.yml`。
