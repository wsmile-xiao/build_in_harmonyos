cmake_minimum_required(VERSION 3.15)
project(test_btas CXX)

# Find the package via Conan-generated CMakeDeps
find_package(btas REQUIRED)

add_executable(test_btas test_btas.cpp)
target_link_libraries(test_btas btas::btas)
set_target_properties(test_btas PROPERTIES CXX_STANDARD 17)
set_target_properties(test_btas PROPERTIES CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_btas COMMAND test_btas)
