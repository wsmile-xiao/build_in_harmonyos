cmake_minimum_required(VERSION 3.15)
project(test_libleidenalg CXX)

find_package(igraph REQUIRED)
find_package(libleidenalg REQUIRED)

add_executable(test_leidenalg test_leidenalg.cpp)
target_link_libraries(test_leidenalg PRIVATE libleidenalg::libleidenalg igraph::igraph)
target_compile_features(test_leidenalg PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_leidenalg COMMAND test_leidenalg)
