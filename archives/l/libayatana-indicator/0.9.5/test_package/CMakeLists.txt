cmake_minimum_required(VERSION 3.15)
project(test_libayatana-indicator C)

# 走 pkg-config 链路（PkgConfigDeps 生成 ayatana-indicator3-0.4.pc 及全部
# 传递依赖 .pc），pkg_check_modules 自动传播 gtk→pango→harfbuzz 等传递
# include/lib 路径（同 ayatana-ido 0.10.4 先例），避免 CMakeDeps 组件图
# 断裂导致 hb.h 找不到。
find_package(PkgConfig REQUIRED)
pkg_check_modules(AYATANA_INDICATOR REQUIRED IMPORTED_TARGET ayatana-indicator3-0.4)

add_executable(test_libayatana-indicator test.c)
target_link_libraries(test_libayatana-indicator PkgConfig::AYATANA_INDICATOR)
# g_test_get_filename(G_TEST_DIST/...) 需要 -DSRCDIR 指向源目录
target_compile_definitions(test_libayatana-indicator PRIVATE SRCDIR="${CMAKE_CURRENT_SOURCE_DIR}")
# ENABLE_IDO=ON 形态：ayatana-indicator3-0.4.pc Requires 含
# libayatana-ido3-0.4 → indicator-ng.h 可达，编译期验证
target_compile_definitions(test_libayatana-indicator PRIVATE WITH_IDO=1)

enable_testing()
add_test(NAME test_libayatana-indicator COMMAND test_libayatana-indicator)
