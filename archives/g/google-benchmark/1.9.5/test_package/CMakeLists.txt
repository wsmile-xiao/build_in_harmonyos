cmake_minimum_required(VERSION 3.15)
project(test_google_benchmark LANGUAGES CXX)

find_package(benchmark CONFIG REQUIRED)

add_executable(test_google_benchmark test.cpp)
target_compile_features(test_google_benchmark PRIVATE cxx_std_17)
target_link_libraries(test_google_benchmark PRIVATE benchmark::benchmark)

enable_testing()
add_test(NAME test_google_benchmark COMMAND test_google_benchmark)