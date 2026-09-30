cmake_minimum_required(VERSION 3.15)
project(test_libvecpf C CXX)

# Find the package via Conan-generated CMakeDeps
find_package(libvecpf REQUIRED)

# The concurrency check in test_vecpf.c needs real threads.
set(THREADS_PREFER_PTHREAD_FLAG ON)
find_package(Threads REQUIRED)

add_executable(test_vecpf test_vecpf.c)
target_link_libraries(test_vecpf libvecpf::libvecpf Threads::Threads)

# test_vecpf_cxx.cpp guards the `extern "C"` linkage of the public header: a
# C++ translation unit must be able to call the C library.
add_executable(test_vecpf_cxx test_vecpf_cxx.cpp)
target_link_libraries(test_vecpf_cxx libvecpf::libvecpf)

enable_testing()
add_test(NAME test_vecpf COMMAND test_vecpf)
add_test(NAME test_vecpf_cxx COMMAND test_vecpf_cxx)
