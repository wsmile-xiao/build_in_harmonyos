cmake_minimum_required(VERSION 3.15)
project(test_eastl CXX)

find_package(eastl CONFIG REQUIRED)

add_executable(test_eastl test.cpp)
target_link_libraries(test_eastl PRIVATE eastl::eastl)

enable_testing()
add_test(NAME test_eastl COMMAND test_eastl)

if(NOT DEFINED EASTL_UPSTREAM_TEST_EXECUTABLE OR
   NOT EXISTS "${EASTL_UPSTREAM_TEST_EXECUTABLE}")
    message(FATAL_ERROR "The packaged upstream EASTLTest runner is missing")
endif()
add_test(NAME EASTLTestRuns COMMAND "${EASTL_UPSTREAM_TEST_EXECUTABLE}")
