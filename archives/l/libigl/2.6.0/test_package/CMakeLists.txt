cmake_minimum_required(VERSION 3.15)
project(test_libigl CXX)

find_package(libigl REQUIRED)

add_executable(test_igl test_igl.cpp)
target_link_libraries(test_igl PRIVATE igl::core)
set_property(TARGET test_igl PROPERTY CXX_STANDARD 17)
set_property(TARGET test_igl PROPERTY CXX_STANDARD_REQUIRED ON)

add_executable(igl_upstream_test upstream_igl_test.cpp)
target_link_libraries(igl_upstream_test PRIVATE igl::core)
set_property(TARGET igl_upstream_test PROPERTY CXX_STANDARD 17)
set_property(TARGET igl_upstream_test PROPERTY CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_igl COMMAND test_igl)
add_test(NAME igl_upstream_test COMMAND igl_upstream_test)
