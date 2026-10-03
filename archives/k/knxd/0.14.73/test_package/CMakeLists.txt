# test_package/CMakeLists.txt -- 编译 test_eibclient（真链接被测包 knxd::knxd）
cmake_minimum_required(VERSION 3.15)
project(knxd_test_package C)

find_package(knxd CONFIG REQUIRED)

add_executable(test_eibclient test_eibclient.c)
target_link_libraries(test_eibclient PRIVATE knxd::knxd)
