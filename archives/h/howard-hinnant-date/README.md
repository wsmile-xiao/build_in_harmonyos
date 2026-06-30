# howard-hinnant-date

现代 C++ 日期时间处理库，Howard Hinnant 开发，基于 C++17 标准。

## 简介

howard-hinnant-date 是一个轻量级、现代化的 C++ 日期时间库，提供：
- **date.h**：header-only 日期/时间处理（年、月、日、时长、格式化）
- **tz.h + date-tz**：可选编译的时区支持库（静态库 libdate-tz.a）
- 多种日历系统：伊斯兰历、ISO 周历、儒略历、太阳回历

## OHOS 适配

### 适配要点

1. **时区数据库缺失**：OpenHarmony 无 `/usr/share/zoneinfo`，date-tz 必须使用 `MANUAL_TZ_DB=ON` 模式
   - 用户需在代码中手动设置时区数据库路径（`date::set_install()`）
   - 不自动下载时区数据（`AUTO_DOWNLOAD=0`, `HAS_REMOTE_API=0`）

2. **libcurl 缺失**：date-tz 默认 `AUTO_DOWNLOAD=1` 需要 libcurl，OpenHarmony 无预编译 curl-devel 包
   - 使用 `MANUAL_TZ_DB=ON` 完全避免 libcurl 依赖

3. **cmake 平台警告**：cmake 输出 "System is unknown to cmake" 关于 HarmonyOS，非致命不影响功能

4. **C++17 标准**：默认 `CMAKE_CXX_STANDARD=17`，clang 15.0.4 完全支持

5. **pthread 依赖**：date-tz 需要 pthread（系统自带）

6. **仅静态库**：默认 `BUILD_SHARED_LIBS=OFF`，编译为 libdate-tz.a 静态库

### 已知问题

- 依赖时区数据库的测试（tz_test、clock_cast_test 的 custom_clock/local_t）在 MANUAL_TZ_DB 模式下会运行时异常
- 纯日期功能（date.h）完全可用，28 个 date_test 全部通过

### 与 Linux 的差异

| 项目 | Linux | OHOS |
|------|-------|------|
| 时区数据库 | /usr/share/zoneinfo | 不存在，需手动配置 |
| libcurl-devel | 通常可用 | 无预编译包 |
| cmake 系统识别 | 已知 | unknown（非致命） |

## 排除与替代

无排除项。date-tz 时区功能在 MANUAL_TZ_DB 模式下可用，但需用户手动配置时区数据路径。

## 依赖

- **编译依赖**：clang 15.0.4+（C++17）、cmake 3.7+、pthread
- **运行依赖**（仅 date-tz 时区功能）：时区数据库（用户自行安装配置）

## 功能验证

```bash
# 纯日期功能验证（header-only，不依赖时区）
clang++ -std=c++17 -I$DEFAULT_PREFIX/include test.cpp -o test && ./test

# date-tz 链接验证（静态库）
clang++ -std=c++17 -I$DEFAULT_PREFIX/include $DEFAULT_PREFIX/lib/libdate-tz.a test_tz.cpp -o test_tz -lpthread && ./test_tz

# 官方测试套件（需 ENABLE_DATE_TESTING=ON 构建）
# date_test: 28/28 PASS
# clock_cast_test: 1/3 PASS（2 个因时区缺失 FAIL）
# solar_hijri_test: 0/1 PASS（因时区缺失 FAIL）
```

## 参考

- GitHub: https://github.com/HowardHinnant/date
- 文档: https://howardhinnant.github.io/date/date.html
- 时区文档: https://howardhinnant.github.io/date/tz.html