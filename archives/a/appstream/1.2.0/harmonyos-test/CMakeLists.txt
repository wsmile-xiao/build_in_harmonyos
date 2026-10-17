cmake_minimum_required(VERSION 3.16)
project(appstream_harmonyos_test LANGUAGES C)

# HarmonyOS 专项测试（可复现构建入口）
# 用法: cmake -S . -B build -DCMAKE_PREFIX_PATH=<appstream 包 prefix> && cmake --build build
# 依赖运行时库: glib/gobject/gio/libxml2/libxmlb/libfyaml/libcurl/zstd/libstemmer/liblzma
#   LD_LIBRARY_PATH 需包含各 conan 依赖 lib 目录
find_package(PkgConfig REQUIRED)
pkg_check_modules(APPSTREAM REQUIRED IMPORTED_TARGET appstream)
pkg_check_modules(APPSTREAM_COMPOSE REQUIRED IMPORTED_TARGET appstream-compose)

add_executable(harmonyos_appstream_test harmonyos_appstream_test.c)
target_link_libraries(harmonyos_appstream_test PRIVATE PkgConfig::APPSTREAM)

# R05 新增：经公开 compose API 驱动真实 media worker 处理 PNG（验证 R05 修复链）
add_executable(harmonyos_compose_test harmonyos_compose_test.c)
target_link_libraries(harmonyos_compose_test PRIVATE PkgConfig::APPSTREAM_COMPOSE PkgConfig::APPSTREAM)

enable_testing()
add_test(NAME harmonyos_appstream_test COMMAND harmonyos_appstream_test)
add_test(NAME harmonyos_compose_test COMMAND harmonyos_compose_test)
