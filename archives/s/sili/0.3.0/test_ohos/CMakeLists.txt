cmake_minimum_required(VERSION 3.15)
project(test_ohos_sili LANGUAGES C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(sili REQUIRED)

add_executable(test_ohos_sili ohos_test.c)
target_link_libraries(test_ohos_sili PRIVATE sili::sili)
