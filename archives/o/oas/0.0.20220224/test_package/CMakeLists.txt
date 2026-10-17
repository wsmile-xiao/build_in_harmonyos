cmake_minimum_required(VERSION 3.16)
project(oas_package_test C)

find_package(oas REQUIRED CONFIG)

add_executable(test_oas test.c)
target_link_libraries(test_oas PRIVATE oas::oas)
find_library(OAS_TEST_DL dl)
if(OAS_TEST_DL)
  target_link_libraries(test_oas PRIVATE ${OAS_TEST_DL})
endif()

file(WRITE ${CMAKE_BINARY_DIR}/test.sh "#!/bin/sh\nset -e\n./test_oas\n")
