cmake_minimum_required(VERSION 3.15)
project(test_embedmq C)

# Find the package via Conan-generated CMakeDeps
find_package(embedmq REQUIRED)

add_executable(test_embedmq test.c)
target_link_libraries(test_embedmq embedmq::embedmq)

# HarmonyOS-specific test: PAL thread + POSIX semaphore dispatch on OHOS runtime
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos embedmq::embedmq pthread)

enable_testing()
add_test(NAME test_embedmq COMMAND test_embedmq)
add_test(NAME test_ohos COMMAND test_ohos)
