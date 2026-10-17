cmake_minimum_required(VERSION 3.15)
project(libcmis_consumer CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(libcmis REQUIRED)

add_executable(test_libcmis test_libcmis.cpp)
target_link_libraries(test_libcmis PRIVATE libcmis::libcmis)
