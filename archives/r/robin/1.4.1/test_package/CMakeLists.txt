cmake_minimum_required(VERSION 3.15)
project(robin_upstream_tests LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(robin_upstream_tests
    upstream_tests/main.cpp
    upstream_tests/custom_allocator_tests.cpp
    upstream_tests/policy_tests.cpp
    upstream_tests/robin_map_tests.cpp
    upstream_tests/robin_set_tests.cpp
)

target_include_directories(robin_upstream_tests PRIVATE
    "${ROBIN_INCLUDE_DIR}"
    "${CMAKE_CURRENT_SOURCE_DIR}/upstream_tests"
)

target_compile_definitions(robin_upstream_tests PRIVATE TSL_DEBUG)
if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    target_compile_options(robin_upstream_tests PRIVATE -Wall -Wextra -Wold-style-cast)
endif()

# The OHOS Boost package provides headers but not the compiled unit_test_framework
# library.  Boost.Test's supported header-only mode supplies the runner while the
# remaining upstream translation units still include <boost/test/unit_test.hpp>.
find_package(Boost REQUIRED)
target_compile_definitions(robin_upstream_tests PRIVATE BOOST_TEST_NO_LIB)
set_source_files_properties(upstream_tests/main.cpp PROPERTIES
    COMPILE_DEFINITIONS "BOOST_TEST_MODULE=robin_map_tests"
    COMPILE_OPTIONS "-include;boost/test/included/unit_test.hpp"
)
target_link_libraries(robin_upstream_tests PRIVATE Boost::headers)
