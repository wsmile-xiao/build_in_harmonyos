cmake_minimum_required(VERSION 3.15)
project(test_opensmtpd-table-redis C)

# Find the package via Conan-generated CMakeDeps
find_package(opensmtpd-table-redis REQUIRED)

add_executable(test_opensmtpd-table-redis test.c)
target_link_libraries(test_opensmtpd-table-redis opensmtpd-table-redis::opensmtpd-table-redis)

enable_testing()
add_test(NAME test_opensmtpd-table-redis COMMAND test_opensmtpd-table-redis)
