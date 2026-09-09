cmake_minimum_required(VERSION 3.15)
project(test_gulrak-filesystem CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(gulrak-filesystem REQUIRED)

add_executable(test_ghc_fs src/test_ghc_fs.cpp)
target_link_libraries(test_ghc_fs gulrak-filesystem::gulrak-filesystem)

enable_testing()
add_test(NAME test_ghc_fs COMMAND test_ghc_fs)