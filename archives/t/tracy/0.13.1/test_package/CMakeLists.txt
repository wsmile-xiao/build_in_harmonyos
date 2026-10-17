cmake_minimum_required(VERSION 3.15)
project(test_tracy CXX)

find_package(tracy REQUIRED)

add_executable(test_tracy test_tracy.cpp)
target_compile_features(test_tracy PRIVATE cxx_std_11)
target_link_libraries(test_tracy PRIVATE tracy::tracy)

enable_testing()
add_test(NAME test_tracy COMMAND test_tracy)
