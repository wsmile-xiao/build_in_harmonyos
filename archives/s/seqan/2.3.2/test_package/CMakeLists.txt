cmake_minimum_required(VERSION 3.15)
project(test_seqan CXX)

# SeqAn 2.3.2 predates C++17; in C++17 mode std::empty() becomes ambiguous
# with seqan::empty(). Force C++14 (profile defaults to cppstd=17).
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(seqan REQUIRED)

add_executable(test_seqan test.cpp)
target_link_libraries(test_seqan seqan::seqan)
target_compile_features(test_seqan PRIVATE cxx_std_14)
# OHOS libc lacks POSIX AIO; seqan's file_async.h must be excluded
target_compile_definitions(test_seqan PRIVATE SEQAN_ASYNC_IO=0)

enable_testing()
add_test(NAME test_seqan COMMAND test_seqan)