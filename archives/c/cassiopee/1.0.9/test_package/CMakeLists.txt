cmake_minimum_required(VERSION 3.15)
project(cassiopee_consumer LANGUAGES CXX)

find_package(cassiopee CONFIG REQUIRED)

add_executable(cassiopee_consumer consumer.cpp)
target_compile_definitions(cassiopee_consumer PRIVATE
    CASSIOPEE_TEST_SEQUENCE="${CMAKE_CURRENT_SOURCE_DIR}/sequence.txt"
)
target_link_libraries(cassiopee_consumer PRIVATE cassiopee::cassiopee)
