cmake_minimum_required(VERSION 3.15)
project(test_libunwind_headers LANGUAGES CXX)

find_package(libunwind-headers CONFIG REQUIRED)

add_executable(test_libunwind_headers test_libunwind_headers.cpp)
target_compile_features(test_libunwind_headers PRIVATE cxx_std_17)
target_link_libraries(test_libunwind_headers PRIVATE libunwind-headers::libunwind-headers)
