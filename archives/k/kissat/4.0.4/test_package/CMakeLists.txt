cmake_minimum_required(VERSION 3.15)
project(test_kissat C)

# Find the package via Conan-generated CMakeDeps
find_package(kissat REQUIRED)

add_executable(test_kissat test.c)
target_link_libraries(test_kissat kissat::kissat)

enable_testing()
add_test(NAME test_kissat COMMAND test_kissat)
