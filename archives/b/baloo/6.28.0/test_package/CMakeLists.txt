cmake_minimum_required(VERSION 3.15)
project(test_baloo CXX)

# KF6BalooConfig.cmake find_dependency() chains resolve through
# CMAKE_PREFIX_PATH (set up in conanfile.py generate() from the direct
# requirements: qtbase, kcoreaddons, kfilemetadata).
find_package(Qt6 REQUIRED COMPONENTS Core)
find_package(KF6CoreAddons REQUIRED)
find_package(KF6FileMetaData REQUIRED)
find_package(KF6Baloo REQUIRED)

add_executable(test_baloo test.cpp)
target_link_libraries(test_baloo KF6::Baloo)

enable_testing()
add_test(NAME test_baloo COMMAND test_baloo)
