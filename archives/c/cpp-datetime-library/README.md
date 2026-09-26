# cpp-datetime-library

CPP-DateTime-library 是一个跨平台的 C++ 日期/时间库（`jed_utils::datetime` / `jed_utils::timespan`），
提供日期时间构造、格式化、运算、闰年判断与时间段（timespan）计算能力。

## 功能概述

- `datetime`：日期时间构造（支持 12/24 小时制）、格式化输出（自定义格式字符串）、
  年/月/日/时/分/秒加减运算、日期差、闰年判断、字符串解析
- `timespan`：天数/小时/分钟/秒构造，总秒/分/小时换算，比较与相等运算
- 纯 C++14/17 实现，无第三方运行时依赖，跨平台（Linux/Windows/macOS/OHOS）

## OHOS 适配

- 构建系统为 CMake，主库静态编译产出 `libdatetime.a`（默认静态，符合 R26）
- 配方在 generate() 中设置 `CMAKE_SYSTEM_NAME=Linux`（OHOS 基于 Linux 内核，E092 知识）
- 上游测试构建期通过 ExternalProject 联网下载 googletest；配方关闭 BUILD_TESTING 保证
  构建确定，上游 191 用例（117 datetime + 74 timespan）使用本地 googletest 1.14.0 单独
  编译运行，全部通过（E342 知识）
- 版本 1.0.2：0 补丁，纯配方层适配

## 版本目录

- `1.0.2/` — 当前适配版本（published）
