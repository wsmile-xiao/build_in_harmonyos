cmake_minimum_required(VERSION 3.15)
project(test_heatshrink C)

find_package(heatshrink REQUIRED)

# Dynamic-allocation flavor (upstream default, HEATSHRINK_DYNAMIC_ALLOC=1
# comes from the heatshrink::dynamic component defines).
add_executable(test_heatshrink_dynamic test_heatshrink_dynamic.c)
target_link_libraries(test_heatshrink_dynamic PRIVATE heatshrink::dynamic)

# Static-allocation flavor (embedded mode, HEATSHRINK_DYNAMIC_ALLOC=0 comes
# from the heatshrink::static component defines).
add_executable(test_heatshrink_static test_heatshrink_static.c)
target_link_libraries(test_heatshrink_static PRIVATE heatshrink::static)

enable_testing()
add_test(NAME heatshrink_dynamic_consumer COMMAND test_heatshrink_dynamic)
add_test(NAME heatshrink_static_consumer COMMAND test_heatshrink_static)
