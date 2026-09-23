cmake_minimum_required(VERSION 3.15)
project(test_openexr LANGUAGES C CXX)

find_package(OpenEXR REQUIRED CONFIG)

add_executable(test_openexr test_package.cpp)
target_link_libraries(test_openexr PRIVATE OpenEXR::OpenEXR)
target_compile_features(test_openexr PRIVATE cxx_std_17)

# 再验证 C API（OpenEXRCore）与 OpenEXRUtil 组件
add_executable(test_core test_core.c)
target_link_libraries(test_core PRIVATE OpenEXR::OpenEXRCore)
