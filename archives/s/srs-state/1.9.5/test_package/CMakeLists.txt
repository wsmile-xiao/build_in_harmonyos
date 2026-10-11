cmake_minimum_required(VERSION 3.15)
project(srs_state_consumer_test C)

# Conan's generated package configs live outside the SDK sysroot.  Keep them
# discoverable when this consumer test runs under the SDK toolchain locally.
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)
find_package(srs-state CONFIG REQUIRED)

add_executable(test_srs_state test.c)
target_link_libraries(test_srs_state PRIVATE srs-state::srs-state)

add_executable(test_srs_state_ohos test_srs_state_ohos.c)
target_link_libraries(test_srs_state_ohos PRIVATE srs-state::srs-state)

enable_testing()
add_test(NAME srs_state_consumer COMMAND test_srs_state)
add_test(NAME srs_state_ohos_consumer COMMAND test_srs_state_ohos)
