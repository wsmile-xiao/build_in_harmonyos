cmake_minimum_required(VERSION 3.15)
project(leatherman_consumer_test CXX)

find_package(leatherman CONFIG REQUIRED)

add_executable(test_leatherman test_leatherman.cpp)
# Upstream pattern: logging macros require a namespace define, normally
# injected by the leatherman CMake macros; Conan consumers pass it here.
target_compile_definitions(test_leatherman PRIVATE
    LEATHERMAN_LOGGING_NAMESPACE="leatherman.test"
    LEATHERMAN_LOGGING_LINE_NUMBERS)
target_link_libraries(test_leatherman PRIVATE
    leatherman::util
    leatherman::locale
    leatherman::logging
    leatherman::json_container
    leatherman::file_util)
