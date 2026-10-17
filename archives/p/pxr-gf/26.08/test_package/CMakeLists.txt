cmake_minimum_required(VERSION 3.15)
project(test_pxr_gf CXX)

find_package(pxr-gf REQUIRED)

add_executable(test_pxr_gf test_pxr_gf.cpp)
target_link_libraries(test_pxr_gf pxr-gf::pxr-gf)
target_compile_features(test_pxr_gf PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_pxr_gf COMMAND test_pxr_gf)
