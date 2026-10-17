cmake_minimum_required(VERSION 3.15)
project(test_ulfius C)

# Find the package via Conan-generated CMakeDeps
find_package(Ulfius REQUIRED)
# ulfius.h 公开头无条件 include gnutls/jansson/zlib/microhttpd/orcania 头；
# CMakeDeps 不把 ulfius 的 cpp_info.requires 展开为消费者的 find_package，故
# 消费者须显式 find + link 这些公开头依赖（见 conanfile.py comments）。
find_package(gnutls REQUIRED)
find_package(jansson REQUIRED)
# 依赖图中的 zlib 为 zlib/1.3.1.1，其 CMakeDeps 暴露的 target 是
# ZLIB::ZLIB（find_package(ZLIB)），而非 zlib::zlib —— 后者是
# zlib/1.3.1.1.1 及更新版本的命名。见 z/zlib/1.3.1.1/conanfile.py 的
# cmake_file_name=ZLIB / cmake_target_name=ZLIB::ZLIB。
find_package(ZLIB REQUIRED)
find_package(libmicrohttpd REQUIRED)
find_package(Orcania REQUIRED)
find_package(Threads REQUIRED)

add_executable(test_ulfius test.c)
target_link_libraries(test_ulfius Ulfius::Ulfius
        gnutls::gnutls jansson::jansson ZLIB::ZLIB
        libmicrohttpd::libmicrohttpd Orcania::Orcania Threads::Threads)

enable_testing()
add_test(NAME test_ulfius COMMAND test_ulfius)
