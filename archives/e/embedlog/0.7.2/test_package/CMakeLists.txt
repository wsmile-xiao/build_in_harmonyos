cmake_minimum_required(VERSION 3.15)
project(test_embedlog C)

# Find the package via Conan-generated CMakeDeps
find_package(embedlog REQUIRED)

add_executable(test_embedlog test.c)
target_link_libraries(test_embedlog embedlog::embedlog)

# HarmonyOS-specific test: real OHOS behaviors (file log + size rotation +
# monotonic-clock timestamp + pthread thread-safety), links installed lib.
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos embedlog::embedlog)

find_package(Threads REQUIRED)
target_link_libraries(test_ohos Threads::Threads)

enable_testing()
add_test(NAME test_embedlog COMMAND test_embedlog)
add_test(NAME test_ohos COMMAND test_ohos)
