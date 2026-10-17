cmake_minimum_required(VERSION 3.15)
project(test_komihash C)

find_package(komihash CONFIG REQUIRED)

add_executable(test_komihash test_komihash.c)
target_link_libraries(test_komihash PRIVATE komihash::komihash)
set_property(TARGET test_komihash PROPERTY C_STANDARD 99)
