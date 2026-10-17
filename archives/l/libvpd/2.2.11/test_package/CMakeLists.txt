cmake_minimum_required(VERSION 3.15)
project(test_libvpd CXX)

# Find the package via Conan-generated CMakeDeps
find_package(libvpd REQUIRED)

add_executable(test_libvpd test.cpp)
target_link_libraries(test_libvpd libvpd::libvpd sqlite3::sqlite3)
target_compile_features(test_libvpd PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_libvpd COMMAND test_libvpd)