cmake_minimum_required(VERSION 3.15)
project(proxy_libintl_package_test C)

find_package(proxy-libintl CONFIG REQUIRED)

add_executable(proxy_libintl_consumer test_package.c)
target_link_libraries(proxy_libintl_consumer PRIVATE proxy-libintl::intl)
target_compile_features(proxy_libintl_consumer PRIVATE c_std_99)

if(CMAKE_C_COMPILER_ID MATCHES "Clang|GNU")
  target_compile_options(proxy_libintl_consumer PRIVATE -Wall -Wextra -Werror)
endif()
