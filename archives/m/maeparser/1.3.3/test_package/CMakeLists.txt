cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# maeparser public headers include boost/dynamic_bitset.hpp, so boost is a
# public (transitive) dependency of the installed package.
find_package(maeparser REQUIRED CONFIG)
find_package(Boost REQUIRED)
find_package(ZLIB REQUIRED)

add_executable(test_package example.cpp)
target_link_libraries(test_package PRIVATE maeparser::maeparser Boost::iostreams zlib::zlib)

# The boost recipe exposes component includedirs as relative paths, which
# CMakeDeps does not expand into absolute data variables; add the package
# include dir explicitly (same approach as the apngasm test_package).
target_include_directories(test_package PRIVATE ${boost_PACKAGE_FOLDER_RELEASE}/include)

enable_testing()
add_test(NAME test_package COMMAND test_package)
