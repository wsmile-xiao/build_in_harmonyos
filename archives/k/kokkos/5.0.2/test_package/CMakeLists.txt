cmake_minimum_required(VERSION 3.20)
project(test_kokkos LANGUAGES CXX)

find_package(Kokkos CONFIG REQUIRED)

add_executable(test_kokkos test.cpp)
target_compile_features(test_kokkos PRIVATE cxx_std_20)
target_link_libraries(test_kokkos PRIVATE Kokkos::kokkos)
