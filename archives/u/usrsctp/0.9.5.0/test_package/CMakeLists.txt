cmake_minimum_required(VERSION 3.15)
project(test_usrsctp C)

# Find the package via Conan-generated CMakeDeps
find_package(usrsctp REQUIRED)

add_executable(test_usrsctp test.c)
target_link_libraries(test_usrsctp usrsctp::usrsctp)

enable_testing()
add_test(NAME test_usrsctp COMMAND test_usrsctp)
