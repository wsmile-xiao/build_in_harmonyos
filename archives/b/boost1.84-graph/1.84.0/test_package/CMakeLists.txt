cmake_minimum_required(VERSION 3.15)
project(test_boost_graph CXX)

find_package(BoostGraph REQUIRED CONFIG COMPONENTS graph)

add_executable(test_boost_graph test_boost_graph.cpp)
target_link_libraries(test_boost_graph PRIVATE BoostGraph::graph)

enable_testing()
add_test(NAME boost_graph_test COMMAND test_boost_graph)
