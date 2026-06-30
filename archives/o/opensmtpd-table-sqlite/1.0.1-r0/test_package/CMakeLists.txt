cmake_minimum_required(VERSION 3.15)
project(test_opensmtpd-table-sqlite C)

# Find the package via Conan-generated CMakeDeps
find_package(opensmtpd-table-sqlite REQUIRED)

add_executable(test_opensmtpd-table-sqlite test.c)
target_link_libraries(test_opensmtpd-table-sqlite opensmtpd-table-sqlite::opensmtpd-table-sqlite)

enable_testing()
add_test(NAME test_opensmtpd-table-sqlite COMMAND test_opensmtpd-table-sqlite)
