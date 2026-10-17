cmake_minimum_required(VERSION 3.15)
project(test_db C)

# Find the package via Conan-generated CMakeDeps
find_package(db REQUIRED)

add_executable(test_db test.c)
target_link_libraries(test_db db::db)

enable_testing()
add_test(NAME test_db COMMAND test_db)
