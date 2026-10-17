cmake_minimum_required(VERSION 3.15)
project(test_libxmu C)

# Find the package via Conan-generated CMakeDeps
find_package(libxmu REQUIRED)

# test.c calls XmuCompareISOLatin1(), exported by the libXmuu component
# (the Xt-independent subset of libXmu).
add_executable(test_libxmu test.c)
target_link_libraries(test_libxmu libxmu::Xmuu)

enable_testing()
add_test(NAME test_libxmu COMMAND test_libxmu)
