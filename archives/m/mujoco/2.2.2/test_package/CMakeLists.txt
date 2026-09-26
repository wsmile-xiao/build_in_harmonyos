cmake_minimum_required(VERSION 3.15)
project(test_mujoco C)

# Find the package via Conan-generated CMakeDeps
find_package(mujoco REQUIRED)

add_executable(test_mujoco test.c)
target_link_libraries(test_mujoco mujoco::mujoco)

enable_testing()
add_test(NAME test_mujoco COMMAND test_mujoco)
