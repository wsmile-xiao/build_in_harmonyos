cmake_minimum_required(VERSION 3.15)
project(test_libgkarrays CXX)

find_package(libGkArrays CONFIG REQUIRED)

add_executable(test_libgkarrays test_package.cpp)
target_link_libraries(test_libgkarrays PRIVATE libGkArrays::libGkArrays)
set_target_properties(test_libgkarrays PROPERTIES
    CXX_STANDARD 11
    CXX_STANDARD_REQUIRED ON
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

enable_testing()
add_test(NAME test_libgkarrays COMMAND test_libgkarrays)
