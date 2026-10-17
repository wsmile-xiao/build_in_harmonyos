cmake_minimum_required(VERSION 3.15)
project(test_libart C)

# Find the package via Conan-generated CMakeDeps
find_package(libart REQUIRED)

add_executable(test_libart test.c)
target_link_libraries(test_libart libart::libart)

enable_testing()
add_test(NAME test_libart COMMAND test_libart)

add_executable(libart_ohos_test test_ohos.c)
add_test(NAME libart_ohos_platform COMMAND libart_ohos_test)
