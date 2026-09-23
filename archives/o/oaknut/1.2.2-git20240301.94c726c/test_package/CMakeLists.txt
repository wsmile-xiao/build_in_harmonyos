cmake_minimum_required(VERSION 3.15)
project(test_oaknut CXX)

# oaknut 是 C++20 header-only 库
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# CMakeDeps (test_package/conanfile.py) 生成 oaknut-config.cmake
find_package(oaknut CONFIG REQUIRED)

add_executable(test_oaknut test_oaknut.cpp)
target_link_libraries(test_oaknut PRIVATE merry::oaknut)
