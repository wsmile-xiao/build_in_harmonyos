cmake_minimum_required(VERSION 3.15)
project(test_mariadb C)

# Find the mariadb recipe we just built via Conan's CMakeDeps generator.
find_package(mariadb REQUIRED)

add_executable(test_mariadb test_mariadb.c)
target_link_libraries(test_mariadb PRIVATE mariadb::mariadb)
