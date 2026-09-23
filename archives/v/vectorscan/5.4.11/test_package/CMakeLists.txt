cmake_minimum_required(VERSION 3.18)
project(test_vectorscan LANGUAGES C CXX)

find_package(vectorscan CONFIG REQUIRED)

add_executable(test_vectorscan test_vectorscan.c)
target_link_libraries(test_vectorscan PRIVATE hs)
set_property(TARGET test_vectorscan PROPERTY LINKER_LANGUAGE CXX)
set_property(TARGET test_vectorscan PROPERTY C_STANDARD 11)
set_property(TARGET test_vectorscan PROPERTY C_STANDARD_REQUIRED ON)
set_property(TARGET test_vectorscan PROPERTY C_EXTENSIONS OFF)

enable_testing()
add_test(NAME vectorscan_consumer COMMAND test_vectorscan)
