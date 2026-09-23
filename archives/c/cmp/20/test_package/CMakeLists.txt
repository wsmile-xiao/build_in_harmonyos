cmake_minimum_required(VERSION 3.15)
project(test_cmp C)

# Find the package via Conan-generated CMakeDeps
find_package(cmp REQUIRED)

add_executable(test_cmp test_package.c)
target_link_libraries(test_cmp cmp::cmp)
# The OHOS no-heap test proves cmp makes zero heap allocations during
# encode/decode via -Wl,--wrap=malloc/free/calloc/realloc counters.
target_link_options(test_cmp PRIVATE
    -Wl,--wrap=malloc,--wrap=free,--wrap=calloc,--wrap=realloc)

enable_testing()
add_test(NAME test_cmp COMMAND test_cmp)