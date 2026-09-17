cmake_minimum_required(VERSION 3.15)
project(test_liblqr C)

find_package(liblqr REQUIRED)
find_package(glib REQUIRED)

add_executable(test_liblqr test.c)
target_link_libraries(test_liblqr liblqr::liblqr)

enable_testing()
add_test(NAME test_liblqr COMMAND test_liblqr)
