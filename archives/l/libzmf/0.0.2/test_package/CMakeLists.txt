cmake_minimum_required(VERSION 3.15)
project(test_libzmf CXX)

# Find packages via Conan-generated CMakeDeps. libzmf's public header
# ZMFDocument.h #includes <librevenge/librevenge.h>, so the test consumer
# must also find librevenge's headers — link its target to surface them.
find_package(libzmf REQUIRED)
find_package(librevenge REQUIRED)

add_executable(test_libzmf test.cpp)
target_link_libraries(test_libzmf libzmf::libzmf librevenge::librevenge)

enable_testing()
add_test(NAME test_libzmf COMMAND test_libzmf)
