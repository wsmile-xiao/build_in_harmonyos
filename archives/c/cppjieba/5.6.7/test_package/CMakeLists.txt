cmake_minimum_required(VERSION 3.15)
project(test_cppjieba CXX)

find_package(cppjieba REQUIRED)

add_executable(test_cppjieba test.cpp)
target_link_libraries(test_cppjieba PRIVATE cppjieba::cppjieba)
set_target_properties(test_cppjieba PROPERTIES CXX_STANDARD 11 CXX_STANDARD_REQUIRED ON)
if(DEFINED CPPJIEBA_DICT_DIR AND NOT CPPJIEBA_DICT_DIR STREQUAL "")
  target_compile_definitions(test_cppjieba PRIVATE CPPJIEBA_DICT_DIR="${CPPJIEBA_DICT_DIR}")
endif()
