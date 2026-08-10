cmake_minimum_required(VERSION 3.15)
project(test_libaccounts-glib C)

# Find the package via Conan-generated CMakeDeps
find_package(libaccounts-glib REQUIRED)

add_executable(test_libaccounts-glib test.c)
target_link_libraries(test_libaccounts-glib libaccounts-glib::libaccounts-glib)

enable_testing()
add_test(NAME test_libaccounts-glib COMMAND test_libaccounts-glib)
