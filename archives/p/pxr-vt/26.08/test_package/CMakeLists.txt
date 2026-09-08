cmake_minimum_required(VERSION 3.15)
project(test_pxr_vt CXX)

find_package(pxr-vt REQUIRED)

add_executable(test_pxr_vt test_pxr_vt.cpp)
target_link_libraries(test_pxr_vt pxr-vt::pxr-vt)
target_compile_features(test_pxr_vt PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_pxr_vt COMMAND test_pxr_vt)
