cmake_minimum_required(VERSION 3.13)
project(test_zmusic CXX)

# Find the package via Conan-generated CMakeDeps
find_package(zmusic REQUIRED)

add_executable(test_zmusic test_package.cpp)
target_link_libraries(test_zmusic PRIVATE ZMusic::zmusic)
