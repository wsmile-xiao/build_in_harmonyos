cmake_minimum_required(VERSION 3.15)
project(test_naive_tsearch C)

# Find the package via Conan-generated CMakeDeps
find_package(naive-tsearch REQUIRED)

# Two consumer translation units, one per packaged flavour:
#  - consumer_static.c:   default search.h -> tsearch.h -> libnaive-tsearch.a
#  - consumer_hdronly.c:  NAIVE_TSEARCH_HDRONLY search.h -> tsearch_hdronly.h
add_executable(naive-tsearch-consumer
    consumer_main.c
    consumer_static.c
    consumer_hdronly.c
)
target_link_libraries(naive-tsearch-consumer PRIVATE naive-tsearch::naive-tsearch)
target_compile_options(naive-tsearch-consumer PRIVATE -Wall -Wextra)
