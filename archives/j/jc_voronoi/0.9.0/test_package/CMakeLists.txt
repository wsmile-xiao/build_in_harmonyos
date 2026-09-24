cmake_minimum_required(VERSION 3.15)
project(test_jc_voronoi C)

find_package(jc_voronoi REQUIRED)

add_executable(test_jc_voronoi test.c)
target_link_libraries(test_jc_voronoi jc_voronoi::jc_voronoi)
target_compile_features(test_jc_voronoi PRIVATE c_std_99)

enable_testing()
add_test(NAME test_jc_voronoi COMMAND test_jc_voronoi)