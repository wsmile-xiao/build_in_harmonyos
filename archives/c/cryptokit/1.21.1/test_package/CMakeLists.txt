cmake_minimum_required(VERSION 3.15)
project(test_cryptokit C)

# Conan CMakeDeps generates cryptokit-config.cmake
find_package(cryptokit REQUIRED CONFIG)

add_executable(test_cryptokit test.c)
target_compile_definitions(test_cryptokit PRIVATE EXPORT=)
target_link_libraries(test_cryptokit PRIVATE cryptokit::cryptokit)
# R34: Verify the test actually links and calls the library
target_link_options(test_cryptokit PRIVATE -Wl,--no-undefined)
