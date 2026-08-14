cmake_minimum_required(VERSION 3.15)
project(test_libde265 C)

# Find the package via Conan-generated CMakeDeps.
# conanfile.py exposes cmake_file_name=libde265, cmake_target_name=libde265::de265.
find_package(libde265 REQUIRED)

add_executable(test_libde265 test.c)
target_link_libraries(test_libde265 libde265::de265)

# libde265 is a C++17 library; the test is a C program, so the C++ runtime
# (libc++) must be linked explicitly. On OHOS/Linux-clang the std::mutex,
# __cxa_guard, operator new/delete etc. live in libc++ and libpthread.
if(NOT MSVC)
    target_link_options(test_libde265 PRIVATE -lc++ -lpthread)
endif()

enable_testing()
add_test(NAME test_libde265 COMMAND test_libde265)
