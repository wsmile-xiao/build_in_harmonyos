cmake_minimum_required(VERSION 3.15)
project(test_gperftools LANGUAGES CXX)

find_package(gperftools CONFIG REQUIRED)

add_executable(test_gperftools test_gperftools.cpp)
target_compile_features(test_gperftools PRIVATE cxx_std_17)
target_link_libraries(test_gperftools PRIVATE gperftools::tcmalloc_minimal)

enable_testing()
add_test(NAME gperftools_consumer COMMAND test_gperftools)
