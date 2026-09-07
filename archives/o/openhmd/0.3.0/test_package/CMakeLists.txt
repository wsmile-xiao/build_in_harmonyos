cmake_minimum_required(VERSION 3.15)
project(test_openhmd C)

set(CMAKE_C_STANDARD 99)

# Find the package via Conan-generated CMakeDeps
find_package(openhmd REQUIRED)

add_executable(test_openhmd test.c)
target_link_libraries(test_openhmd PRIVATE openhmd::openhmd)

# 数学函数（fabsf 等）需要 libm（上游 unittests_LDADD 也带 -lm）
if(UNIX)
    target_link_libraries(test_openhmd PRIVATE m)
endif()

enable_testing()
add_test(NAME test_openhmd COMMAND test_openhmd)
