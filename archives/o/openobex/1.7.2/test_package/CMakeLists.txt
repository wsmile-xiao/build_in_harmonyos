cmake_minimum_required(VERSION 3.15)
project(test_openobex C)

find_package(OpenObex REQUIRED CONFIG)

add_executable(test_openobex test_openobex.c)
target_link_libraries(test_openobex PRIVATE OpenObex::openobex)
