cmake_minimum_required(VERSION 3.15)
project(test_graphene C)

# Find the package via Conan-generated CMakeDeps.
find_package(graphene REQUIRED)

add_executable(test_graphene test_graphene.c)
target_link_libraries(test_graphene graphene::graphene)

enable_testing()
add_test(NAME test_graphene COMMAND test_graphene)
