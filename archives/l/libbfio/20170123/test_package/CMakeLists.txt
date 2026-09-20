cmake_minimum_required(VERSION 3.15)
project(test_bfio C)

find_package(libbfio REQUIRED)

# A C consumer that links the installed static library and drives the
# public file/handle API against a real file (see test.c).
add_executable(test_bfio test.c)
target_link_libraries(test_bfio PRIVATE libbfio::libbfio)

enable_testing()
add_test(NAME test_bfio COMMAND test_bfio)
