cmake_minimum_required(VERSION 3.15)
project(test_kuba-zip C)

# Find the package via Conan-generated CMakeDeps
find_package(kuba-zip REQUIRED)

add_executable(test_kuba-zip test.c)
target_link_libraries(test_kuba-zip kuba-zip::kuba-zip)

enable_testing()
add_test(NAME test_kuba-zip COMMAND test_kuba-zip)
