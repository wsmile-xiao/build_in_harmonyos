cmake_minimum_required(VERSION 3.15)
project(test_opensmtpd-filter-senderscore C)

# Find the package via Conan-generated CMakeDeps
find_package(opensmtpd-filter-senderscore REQUIRED)

add_executable(test_opensmtpd-filter-senderscore test.c)
target_link_libraries(test_opensmtpd-filter-senderscore opensmtpd-filter-senderscore::opensmtpd-filter-senderscore)

enable_testing()
add_test(NAME test_opensmtpd-filter-senderscore COMMAND test_opensmtpd-filter-senderscore)
