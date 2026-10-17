# chrono (Howard Hinnant date)

chrono is the Conan package name used in this repository for Howard Hinnant's
date library — a C++ library for civil calendars, date formatting and parsing,
ISO week dates, additional calendars, and timezone handling built on
`std::chrono`.

## 功能概述

- Gregorian 日期构造、算术、格式化与解析
- ISO week、Julian、Islamic 与 Solar Hijri 日历
- `date-tz` 时区数据库和 zoned time API

## OHOS 适配

OHOS 配方同时提供 `date::date` 与 `date::date-tz`。时区库采用 manual tzdb
模式，不假设设备存在 Linux `/usr/share/zoneinfo`，也不隐式依赖 curl；应用
负责提供 tzdata 目录并调用 `date::set_install()`。

## 依赖关系

无 Conan 三方依赖。编译后的 `date-tz` 使用 OHOS 系统 pthread。

## 参考资料

- https://github.com/HowardHinnant/date
- https://github.com/HowardHinnant/date/releases/tag/v3.0.4
