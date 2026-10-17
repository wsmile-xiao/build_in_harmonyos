cmake_minimum_required(VERSION 3.15)
project(test_libayatana C)

# 走 pkg-config 链路（PkgConfigDeps 生成 ayatana-indicator3-0.4.pc 及全部
# 传递依赖 .pc），pkg_check_modules 自动传播 gtk→pango→harfbuzz(hb.h)
# 等传递 include（同 ayatana-ido/gtk 先例），避免 CMakeDeps 组件图断裂
# 导致 pango-coverage.h 找不到 hb.h。
find_package(PkgConfig REQUIRED)
pkg_check_modules(AYATANA_INDICATOR REQUIRED IMPORTED_TARGET ayatana-indicator3-0.4)

add_executable(test_libayatana test.c)
target_link_libraries(test_libayatana PkgConfig::AYATANA_INDICATOR)

enable_testing()
add_test(NAME test_libayatana COMMAND test_libayatana)