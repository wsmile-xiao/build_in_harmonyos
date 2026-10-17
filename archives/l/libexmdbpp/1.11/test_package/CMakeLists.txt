cmake_minimum_required(VERSION 3.15)
project(test_libexmdbpp CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# The end-to-end cases start an exmdb server simulator in a background thread
set(THREADS_PREFER_PTHREAD_FLAG ON)
find_package(Threads REQUIRED)

# Find the package via Conan-generated CMakeDeps
find_package(libexmdbpp REQUIRED)

add_executable(test_libexmdbpp test.cpp)
target_link_libraries(test_libexmdbpp libexmdbpp::libexmdbpp Threads::Threads)

enable_testing()
add_test(NAME test_libexmdbpp COMMAND test_libexmdbpp)
