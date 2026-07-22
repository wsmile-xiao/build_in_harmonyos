cmake_minimum_required(VERSION 3.15)
project(test_spectra CXX)

find_package(Spectra REQUIRED)

add_executable(test_spectra test_spectra.cpp)
target_link_libraries(test_spectra PRIVATE Spectra::Spectra)
