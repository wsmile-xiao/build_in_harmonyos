cmake_minimum_required(VERSION 3.15)
project(test_enkits C)

# Find the package via Conan-generated CMakeDeps.
# conanfile.py exposes cmake_file_name=enkiTS, cmake_target_name=enkiTS::enkiTS.
find_package(enkiTS REQUIRED)

add_executable(test_enkits test.c)
target_link_libraries(test_enkits enkiTS::enkiTS)

# enkiTS is a C++11 library; the test is a C program, so the C++ runtime
# (libc++) must be linked explicitly. On OHOS/Linux-clang the std::thread,
# std::mutex, __cxa_guard etc. live in libc++ and libpthread.
if(NOT MSVC)
    target_link_options(test_enkits PRIVATE -lc++ -lpthread)
endif()

enable_testing()
add_test(NAME test_enkits COMMAND test_enkits)
