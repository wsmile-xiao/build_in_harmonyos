cmake_minimum_required(VERSION 3.15)
project(test_foonathan_memory LANGUAGES CXX)

enable_testing()
find_package(foonathan_memory CONFIG REQUIRED)

add_executable(test_foonathan_memory test.cpp)
target_compile_features(test_foonathan_memory PRIVATE cxx_std_11)
target_link_libraries(test_foonathan_memory PRIVATE foonathan_memory)
add_test(NAME test_foonathan_memory COMMAND test_foonathan_memory)
