cmake_minimum_required(VERSION 3.15)
project(test_tinyexr CXX)

find_package(tinyexr REQUIRED)

add_executable(test_tinyexr test_tinyexr.cpp)
target_link_libraries(test_tinyexr PRIVATE tinyexr::tinyexr)
target_compile_features(test_tinyexr PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_tinyexr COMMAND test_tinyexr)
