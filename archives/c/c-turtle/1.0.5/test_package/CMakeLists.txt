cmake_minimum_required(VERSION 3.15)
project(test_c-turtle CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(c-turtle REQUIRED)

add_executable(test_cturtle src/test_cturtle.cpp)
target_link_libraries(test_cturtle c-turtle::c-turtle)

# HarmonyOS 专项测试：headless Koch 分形渲染 + GIF 输出验证（与消费者用例分别计数）
add_executable(test_fractal src/test_fractal.cpp)
target_link_libraries(test_fractal c-turtle::c-turtle)

enable_testing()
add_test(NAME test_cturtle COMMAND test_cturtle)
add_test(NAME test_fractal COMMAND test_fractal)