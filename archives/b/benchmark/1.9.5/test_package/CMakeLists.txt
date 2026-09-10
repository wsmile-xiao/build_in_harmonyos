cmake_minimum_required(VERSION 3.15)
project(test_benchmark LANGUAGES CXX)

find_package(benchmark CONFIG REQUIRED)

add_executable(test_benchmark test.cpp)
target_link_libraries(test_benchmark PRIVATE benchmark::benchmark)

add_executable(test_benchmark_main test_main.cpp)
target_link_libraries(test_benchmark_main PRIVATE benchmark::benchmark_main)

foreach(target IN ITEMS test_benchmark test_benchmark_main)
  set_property(TARGET ${target} PROPERTY CXX_STANDARD 17)
  set_property(TARGET ${target} PROPERTY CXX_STANDARD_REQUIRED ON)
  set_property(TARGET ${target} PROPERTY CXX_EXTENSIONS OFF)
endforeach()

enable_testing()
add_test(
  NAME consumer_benchmark
  COMMAND test_benchmark --benchmark_min_time=0.001s
)
add_test(
  NAME consumer_benchmark_main
  COMMAND test_benchmark_main --benchmark_min_time=0.001s
)
