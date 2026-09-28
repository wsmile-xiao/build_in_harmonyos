cmake_minimum_required(VERSION 3.15)
project(test_vlc C)

find_package(vlc REQUIRED CONFIG)

add_executable(test_vlc src/test_vlc.c)
target_link_libraries(test_vlc vlc::vlc)

# 测试目标不安装，仅由 ctest 运行
enable_testing()
add_test(NAME test_vlc COMMAND test_vlc)
