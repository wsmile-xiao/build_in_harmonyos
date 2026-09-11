cmake_minimum_required(VERSION 3.15)
project(test_ktx C CXX)

find_package(ktx-software REQUIRED)

add_executable(test_ktx test.c)
target_link_libraries(test_ktx ktx-software::ktx-software)

enable_testing()
add_test(NAME test_ktx COMMAND test_ktx)
