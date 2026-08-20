cmake_minimum_required(VERSION 3.15)
project(test_enet C)

# Find the package via Conan-generated CMakeDeps
find_package(enet REQUIRED)

add_executable(test_enet test.c)
target_link_libraries(test_enet enet::enet)

enable_testing()
add_test(NAME test_enet COMMAND test_enet)
