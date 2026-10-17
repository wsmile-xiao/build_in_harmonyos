cmake_minimum_required(VERSION 3.15)
project(test_lwmem C CXX)

# Find the package via Conan-generated CMakeDeps
find_package(lwmem REQUIRED)

# lwmem requires a user-provided lwmem_opts.h (see lwmem_opt.h); the
# test_package ships one in this directory.
include_directories(${CMAKE_CURRENT_SOURCE_DIR})

add_executable(test_lwmem test.c)
target_link_libraries(test_lwmem lwmem::lwmem)

add_executable(test_lwmem_ohos ohos_special_test.cpp)
target_link_libraries(test_lwmem_ohos lwmem::lwmem)

enable_testing()
add_test(NAME test_lwmem COMMAND test_lwmem)
add_test(NAME test_lwmem_ohos COMMAND test_lwmem_ohos)