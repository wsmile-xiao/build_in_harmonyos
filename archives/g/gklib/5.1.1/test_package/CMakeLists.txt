cmake_minimum_required(VERSION 3.15)
project(gklib_consumer LANGUAGES C)

find_package(GKlib CONFIG REQUIRED)

add_executable(test_gklib test_package.c)
target_link_libraries(test_gklib PRIVATE GKlib::GKlib)
set_target_properties(test_gklib PROPERTIES
    C_STANDARD 99
    C_STANDARD_REQUIRED ON
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
