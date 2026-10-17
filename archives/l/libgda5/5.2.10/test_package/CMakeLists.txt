cmake_minimum_required(VERSION 3.15)
project(test_libgda5 C)

# 用 pkg-config 消费被测包（PkgConfigDeps 已生成 libgda-5.0.pc 及其依赖 .pc）
find_package(PkgConfig REQUIRED)
pkg_check_modules(GDA REQUIRED IMPORTED_TARGET libgda-5.0)

# 消费者功能测试：SQLite provider + 真实 SQL 往返
add_executable(test_libgda test_libgda.c)
target_link_libraries(test_libgda PkgConfig::GDA)

# HarmonyOS 专项测试：平台守卫 / 插件动态加载 / UTF-8 / 文件型数据库
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos PkgConfig::GDA)

enable_testing()
add_test(NAME test_libgda COMMAND test_libgda)
add_test(NAME test_ohos COMMAND test_ohos)
