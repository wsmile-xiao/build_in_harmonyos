cmake_minimum_required(VERSION 3.15)
project(test_libaccounts C)

find_package(libaccounts REQUIRED)

add_executable(test_libaccounts test_package.c)
target_link_libraries(test_libaccounts PRIVATE libaccounts::libaccounts)
