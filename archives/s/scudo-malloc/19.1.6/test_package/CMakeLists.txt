cmake_minimum_required(VERSION 3.15)
project(test_scudo_malloc C)

# This test uses dlopen to load the shared library at runtime,
# avoiding static linking which overrides system malloc and crashes on OHOS.
add_executable(test_scudo_malloc test.c)
target_link_libraries(test_scudo_malloc dl)

enable_testing()
add_test(NAME test_scudo_malloc COMMAND test_scudo_malloc $ENV{SCUDO_LIB_PATH})
