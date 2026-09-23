cmake_minimum_required(VERSION 3.15)
project(test_gupnp C)

# Find the package via Conan-generated CMakeDeps (cmake_file_name=gupnp-1.6).
# ⚠️ 只链 gupnp-1.6：glib/gobject/soup/gssdp/xml2 符号经 libgupnp-1.6.so 的
# NEEDED libsoup-3.0.so 解析（单 gobject 副本教义，gssdp 1.6.6 铁证）。显式
# 链 glib2/libsoup3 会让静态 glib 进入测试可执行文件 → GObject 双副本
# SIGABRT（g_type_register_static assertion）。
find_package(gupnp-1.6 CONFIG REQUIRED)

add_executable(test_gupnp test_gupnp.c)
target_link_libraries(test_gupnp PRIVATE gupnp-1.6::gupnp-1.6)

enable_testing()
add_test(NAME test_gupnp COMMAND test_gupnp)
