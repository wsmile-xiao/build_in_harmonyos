cmake_minimum_required(VERSION 3.15)
project(test_opensmtpd-table-socketmap C)

# Find the package via Conan-generated CMakeDeps
find_package(opensmtpd-table-socketmap REQUIRED)

add_executable(test_opensmtpd-table-socketmap test.c)
target_link_libraries(test_opensmtpd-table-socketmap opensmtpd-table-socketmap::opensmtpd-table-socketmap)

enable_testing()
add_test(NAME test_opensmtpd-table-socketmap COMMAND test_opensmtpd-table-socketmap)
