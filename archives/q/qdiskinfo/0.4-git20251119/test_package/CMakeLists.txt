cmake_minimum_required(VERSION 3.16)
project(test_qdiskinfo LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# qtbase 以 cmake_find_mode=none 导出：Qt6Config.cmake 由 Qt 自身安装，
# 通过 generate() 写入的 CMAKE_PREFIX_PATH 定位。
find_package(Qt6 REQUIRED COMPONENTS Core)

add_executable(test_qdiskinfo test_qdiskinfo.cpp)
target_link_libraries(test_qdiskinfo PRIVATE Qt6::Core)
