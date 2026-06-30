cmake_minimum_required(VERSION 3.15)
project(test_opensmtpd-filter-dkimsign C)

# Find the package via Conan-generated CMakeDeps
find_package(opensmtpd-filter-dkimsign REQUIRED)

add_executable(test_opensmtpd-filter-dkimsign test.c)
target_link_libraries(test_opensmtpd-filter-dkimsign opensmtpd-filter-dkimsign::opensmtpd-filter-dkimsign)

enable_testing()
add_test(NAME test_opensmtpd-filter-dkimsign COMMAND test_opensmtpd-filter-dkimsign)
