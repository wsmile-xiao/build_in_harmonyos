cmake_minimum_required(VERSION 3.15)
project(test_gssdp C)

# Find the package via Conan-generated CMakeDeps (cmake_file_name=gssdp-1.6).
# ⚠️ 只链 gssdp-1.6：glib/gobject/soup 符号经 libgssdp-1.6.so 的 NEEDED
# libsoup-3.0.so 解析（单 gobject 副本）。显式链 glib2/libsoup3 会让静态
# glib 进入测试可执行文件 → GObject 双副本 SIGABRT（见 conanfile 注释）。
find_package(gssdp-1.6 CONFIG REQUIRED)

add_executable(test_gssdp test_gssdp.c)
target_link_libraries(test_gssdp PRIVATE gssdp-1.6::gssdp-1.6)

enable_testing()
add_test(NAME test_gssdp COMMAND test_gssdp)
