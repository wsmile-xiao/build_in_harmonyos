cmake_minimum_required(VERSION 3.15)
project(test_libqalculate CXX)

# Find the package via Conan-generated CMakeDeps
find_package(libqalculate REQUIRED)
find_package(gmp REQUIRED)
find_package(mpfr REQUIRED)
find_package(LibXml2 REQUIRED)
find_package(readline REQUIRED)

add_executable(test_libqalculate test.cpp)
target_link_libraries(test_libqalculate
    libqalculate::libqalculate
    gmp::gmp
    mpfr::mpfr
    LibXml2::LibXml2
    readline::readline)

enable_testing()
add_test(NAME test_libqalculate COMMAND test_libqalculate)