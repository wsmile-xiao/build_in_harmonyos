cmake_minimum_required(VERSION 3.15)
project(test_gsl_lite CXX)

find_package(gsl-lite REQUIRED)

add_executable(test_gsl_lite test.cpp)
target_link_libraries(test_gsl_lite PRIVATE gsl::gsl)
target_compile_definitions(test_gsl_lite PRIVATE gsl_CONFIG_DEFAULTS_VERSION=1)
set_target_properties(test_gsl_lite PROPERTIES CXX_STANDARD 11 CXX_STANDARD_REQUIRED ON)
