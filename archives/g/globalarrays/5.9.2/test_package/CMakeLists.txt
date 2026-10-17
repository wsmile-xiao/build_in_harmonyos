cmake_minimum_required(VERSION 3.15)
project(ga_test C)

find_package(globalarrays REQUIRED CONFIG)
# mpich 依赖：CMakeDeps 按 recipe 的 cmake_target_name 生成 MPI::MPI_C
find_package(MPI REQUIRED CONFIG)

add_executable(test_ga test_ga.c)
target_link_libraries(test_ga PRIVATE globalarrays::globalarrays MPI::MPI_C)
