cmake_minimum_required(VERSION 3.15)
project(test_dvector C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

# dvector 为 header-only 库，通过 Conan 生成的 CMakeDeps 配置查找
find_package(dvector CONFIG REQUIRED)

add_executable(test_dvector test.c)
target_link_libraries(test_dvector PRIVATE dvector::dvector)

enable_testing()
add_test(NAME test_dvector COMMAND test_dvector)
