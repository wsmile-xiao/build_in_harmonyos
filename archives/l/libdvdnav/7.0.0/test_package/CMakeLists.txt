cmake_minimum_required(VERSION 3.15)
project(test_libdvdnav C)

find_package(libdvdnav REQUIRED CONFIG)

add_executable(test_libdvdnav test_libdvdnav.c)
target_link_libraries(test_libdvdnav libdvdnav::libdvdnav)

# 测试目标不安装，仅由 ctest 运行
enable_testing()
add_test(NAME test_libdvdnav COMMAND test_libdvdnav)
