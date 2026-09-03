cmake_minimum_required(VERSION 3.15)
project(test_sqlite_orm CXX)

# Find the package via Conan-generated CMakeDeps
find_package(sqlite_orm REQUIRED)

add_executable(test_sqlite_orm test.cpp)
target_link_libraries(test_sqlite_orm sqlite_orm::sqlite_orm)

enable_testing()
add_test(NAME test_sqlite_orm COMMAND test_sqlite_orm)