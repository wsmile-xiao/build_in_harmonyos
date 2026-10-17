cmake_minimum_required(VERSION 3.15)
project(test_cxxgraph CXX)

# Find the package via Conan-generated CMakeDeps
find_package(CXXGraph REQUIRED)

add_executable(test_cxxgraph test.cpp)
target_link_libraries(test_cxxgraph CXXGraph::CXXGraph)
target_compile_features(test_cxxgraph PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_cxxgraph COMMAND test_cxxgraph)
