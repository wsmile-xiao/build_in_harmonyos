cmake_minimum_required(VERSION 3.15)
project(test_libplctag C)

# Find the package via Conan-generated CMakeDeps
find_package(libplctag REQUIRED)

add_executable(test_libplctag test.c)
target_link_libraries(test_libplctag libplctag::libplctag)

enable_testing()
add_test(NAME test_libplctag COMMAND test_libplctag)

# HarmonyOS-specific test: tag lifecycle + version + error decode
add_executable(ohos_test ohos_test.c)
target_link_libraries(ohos_test libplctag::libplctag)
add_test(NAME ohos_test COMMAND ohos_test)
