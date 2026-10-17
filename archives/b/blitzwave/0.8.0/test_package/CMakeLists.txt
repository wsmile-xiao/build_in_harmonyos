cmake_minimum_required(VERSION 3.15)
project(test_blitzwave CXX)

# blitzwave headers #include <blitz/array.h>, so the blitz dependency is
# needed at consumer compile time too (CMakeDeps provides blitz::blitz).
find_package(blitz REQUIRED)
find_package(blitzwave REQUIRED)

add_executable(test_blitzwave test_blitzwave.cpp)
target_link_libraries(test_blitzwave blitzwave::blitzwave blitz::blitz)
target_compile_features(test_blitzwave PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_blitzwave COMMAND test_blitzwave)
