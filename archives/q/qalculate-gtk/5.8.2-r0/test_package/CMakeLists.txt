cmake_minimum_required(VERSION 3.15)
project(test_qalculate_gtk CXX)

# Find the packages via Conan-generated CMakeDeps
find_package(qalculate-gtk REQUIRED)
find_package(libqalculate REQUIRED)
find_package(gmp REQUIRED)
find_package(mpfr REQUIRED)
find_package(LibXml2 REQUIRED)
find_package(readline REQUIRED)

add_executable(test_qalculate_gtk test.cpp)
target_link_libraries(test_qalculate_gtk
    qalculate-gtk::qalculate-gtk
    libqalculate::libqalculate
    gmp::gmp
    mpfr::mpfr
    LibXml2::LibXml2
    readline::readline)

enable_testing()
add_test(NAME test_qalculate_gtk COMMAND test_qalculate_gtk)