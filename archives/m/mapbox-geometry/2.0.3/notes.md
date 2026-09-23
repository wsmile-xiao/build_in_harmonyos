# mapbox-geometry 2.0.3 适配记录

- 类型：纯 header-only C++14 库，无编译产物，对外暴露 `mapbox::geometry` 接口目标。
- 唯一 Conan 依赖：`mapbox-variant/1.2.0`（`geometry.hpp` 内 `mapbox::util::variant` 所需；point/line_string/polygon 等核心类型零依赖）。
- 上游测试：`test/` 下 14 个文件（含 `main.cpp`，`CATCH_CONFIG_MAIN` + Catch 1.9.6），共 32 个 `TEST_CASE`；上游 CMake 经 mason 拉取 catch 1.9.6 / variant 1.1.5 / benchmark，OHOS 配方绕开 mason，直接以 `-std=c++14` 编译 `test/*.cpp` 并运行 `./unit-tests`。
- 适配边界：只复制 `include/mapbox/**/*.hpp`，不继承上游 `-Werror -march=native` 等主机调优旗标；OHOS 包装器注入的链接参数以 `-Wno-unused-command-line-argument` 抑制，不触碰任何测试断言。
- 消费者验证：`test_package` 以 `find_package(mapbox-geometry)` + `find_package(mapbox-variant)` 双包联动，覆盖 point / line_string / polygon / geometry variant / geometry_collection / envelope / for_each_point / feature / io 共 8 组断言。
