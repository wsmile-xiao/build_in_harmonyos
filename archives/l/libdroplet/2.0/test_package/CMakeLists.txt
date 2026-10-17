cmake_minimum_required(VERSION 3.15)
project(test_libdroplet C)

# Find the package via Conan-generated CMakeDeps
find_package(libdroplet REQUIRED)
find_package(openssl REQUIRED)
find_package(LibXml2 REQUIRED)
find_package(json-c REQUIRED)

add_executable(test_libdroplet test.c)
# droplet.h 无条件 include openssl/libxml/json-c 头文件，须显式链接
# 各依赖 target 以获取其 include 路径（传递头文件可达）
target_link_libraries(test_libdroplet libdroplet::libdroplet openssl::openssl LibXml2::LibXml2 json-c::json-c)

enable_testing()
add_test(NAME test_libdroplet COMMAND test_libdroplet)