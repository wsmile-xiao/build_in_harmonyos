cmake_minimum_required(VERSION 3.15)
project(test_libwacom C)

find_package(libwacom REQUIRED)

add_executable(test_libwacom test_libwacom.c)
target_link_libraries(test_libwacom PRIVATE libwacom::libwacom)

enable_testing()
add_test(NAME test_libwacom COMMAND test_libwacom ${LIBWACOM_DATA_DIR})
