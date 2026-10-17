cmake_minimum_required(VERSION 3.15)
project(test_libkdtree LANGUAGES CXX)

# CMakeDeps generates libkdtree-config.cmake from the recipe's cpp_info, so the
# consumer resolves the packaged headers through the standard target.
find_package(libkdtree CONFIG REQUIRED)

add_executable(test_libkdtree test_libkdtree.cpp)
target_compile_features(test_libkdtree PRIVATE cxx_std_11)
target_link_libraries(test_libkdtree PRIVATE libkdtree::libkdtree)

enable_testing()
add_test(NAME test_libkdtree COMMAND test_libkdtree)
