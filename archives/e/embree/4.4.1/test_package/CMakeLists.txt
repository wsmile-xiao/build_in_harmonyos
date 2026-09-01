cmake_minimum_required(VERSION 3.15)
project(test_embree CXX)

# Find the package via Conan-generated CMakeDeps
find_package(embree REQUIRED)

add_executable(test_embree test.cpp)
target_link_libraries(test_embree embree::embree)

enable_testing()
add_test(NAME test_embree COMMAND test_embree)
