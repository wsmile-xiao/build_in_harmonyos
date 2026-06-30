cmake_minimum_required(VERSION 3.15)
project(test_opensmtpd-table-passwd C)

# Find the package via Conan-generated CMakeDeps
find_package(opensmtpd-table-passwd REQUIRED)

add_executable(test_opensmtpd-table-passwd test.c)
target_link_libraries(test_opensmtpd-table-passwd opensmtpd-table-passwd::opensmtpd-table-passwd)

enable_testing()
add_test(NAME test_opensmtpd-table-passwd COMMAND test_opensmtpd-table-passwd)
