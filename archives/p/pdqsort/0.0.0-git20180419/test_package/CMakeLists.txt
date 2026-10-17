cmake_minimum_required(VERSION 3.15)
project(pdqsort_consumer CXX)

enable_testing()

find_package(pdqsort CONFIG REQUIRED)

add_executable(pdqsort_consumer test_pdqsort.cpp)
target_link_libraries(pdqsort_consumer PRIVATE pdqsort::pdqsort)
set_target_properties(pdqsort_consumer PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON)

add_test(NAME consumer_assertions COMMAND pdqsort_consumer)
