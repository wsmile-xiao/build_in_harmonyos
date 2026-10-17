cmake_minimum_required(VERSION 3.15)
project(test_scalapack C)

find_package(scalapack CONFIG REQUIRED)

add_executable(test_scalapack test_scalapack.c)
target_compile_features(test_scalapack PRIVATE c_std_99)
target_link_libraries(test_scalapack PRIVATE scalapack::scalapack)
