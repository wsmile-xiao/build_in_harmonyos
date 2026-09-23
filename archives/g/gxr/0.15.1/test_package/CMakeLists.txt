cmake_minimum_required(VERSION 3.15)
project(gxr_test LANGUAGES CXX)

find_package(gxr REQUIRED CONFIG)

add_executable(gxr_test gxr_test.cpp)
target_compile_features(gxr_test PRIVATE cxx_std_17)
target_link_libraries(gxr_test PRIVATE gxr::gxr)

enable_testing()
add_test(NAME gxr_test COMMAND gxr_test)
