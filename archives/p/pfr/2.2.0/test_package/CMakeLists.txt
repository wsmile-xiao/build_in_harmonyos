cmake_minimum_required(VERSION 3.15)
project(test_pfr CXX)

find_package(pfr CONFIG REQUIRED)

add_executable(test_pfr test.cpp)
target_link_libraries(test_pfr PRIVATE boost::pfr)
target_compile_features(test_pfr PRIVATE cxx_std_17)

add_executable(test_pfr_cxx20 test_cxx20.cpp)
target_link_libraries(test_pfr_cxx20 PRIVATE boost::pfr)
target_compile_features(test_pfr_cxx20 PRIVATE cxx_std_20)

enable_testing()
add_test(NAME test_pfr COMMAND test_pfr)
add_test(NAME test_pfr_cxx20 COMMAND test_pfr_cxx20)
