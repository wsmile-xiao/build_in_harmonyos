cmake_minimum_required(VERSION 3.15)
project(test_clthreads LANGUAGES CXX)

find_package(clthreads CONFIG REQUIRED)

add_executable(test_clthreads test_clthreads.cpp)
target_link_libraries(test_clthreads PRIVATE clthreads::clthreads)

add_executable(test_clthreads_threads test_clthreads_threads.cpp)
target_link_libraries(test_clthreads_threads PRIVATE clthreads::clthreads)

foreach(t test_clthreads test_clthreads_threads)
    set_target_properties(${t} PROPERTIES
        CXX_STANDARD 11
        CXX_STANDARD_REQUIRED YES
        RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
endforeach()
