cmake_minimum_required(VERSION 3.15)
project(test_soci CXX)

# Find the package via Conan-generated CMakeDeps
find_package(soci REQUIRED)
# sqlite3: soci-sqlite3.h includes <sqlite3.h>; pulled in directly so CMakeDeps
# emits its config (see test_package/conanfile.py requirements comment).
find_package(sqlite3 REQUIRED)

add_executable(test_soci test.cpp)
target_link_libraries(test_soci PRIVATE soci::soci sqlite3::sqlite3)

enable_testing()
add_test(NAME test_soci COMMAND test_soci)
