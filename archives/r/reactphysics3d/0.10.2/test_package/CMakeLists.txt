cmake_minimum_required(VERSION 3.15)
project(test_reactphysics3d CXX)

# Find the package via Conan-generated CMakeDeps
find_package(ReactPhysics3D REQUIRED)

add_executable(test_reactphysics3d test.cpp)
target_link_libraries(test_reactphysics3d reactphysics3d)

enable_testing()
add_test(NAME test_reactphysics3d COMMAND test_reactphysics3d)