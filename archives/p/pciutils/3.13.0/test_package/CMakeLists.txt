cmake_minimum_required(VERSION 3.15)
project(test_pciutils C)

find_package(pciutils REQUIRED)

add_executable(test_pciutils test.c)
target_link_libraries(test_pciutils pciutils::pciutils)
