cmake_minimum_required(VERSION 3.15)
project(test_libtrng CXX)

# TRNG 4.28 targets C++11 (upstream CMakeLists sets CMAKE_CXX_STANDARD 11).
# The library's headers use C++11 constexpr that does not compile under the
# stricter C++17 constexpr rules set by the conan profile.  Match the
# library's standard so the consumer test exercises the real headers.
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(trng4 REQUIRED)

add_executable(test_libtrng test_libtrng.cc)
target_link_libraries(test_libtrng PRIVATE trng4::trng4)

enable_testing()
add_test(NAME test_libtrng COMMAND test_libtrng)
