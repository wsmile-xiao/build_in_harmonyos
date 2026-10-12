cmake_minimum_required(VERSION 3.15)
project(test_gmp C)

# Find the package via Conan-generated CMakeDeps
find_package(gmp REQUIRED)

add_executable(test_gmp test.c)
target_link_libraries(test_gmp gmp::gmp)

add_executable(ohos_test ohos_test.c)
target_link_libraries(ohos_test gmp::gmp)

enable_testing()
add_test(NAME test_gmp COMMAND test_gmp)
add_test(NAME ohos_test COMMAND ohos_test)
