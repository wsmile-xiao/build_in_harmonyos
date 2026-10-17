cmake_minimum_required(VERSION 3.15)
project(test_libxdf CXX)

# libxdf is consumed through the Conan-generated CMakeDeps config.
find_package(libxdf REQUIRED)

add_executable(test_libxdf test.cpp)
target_link_libraries(test_libxdf PRIVATE libxdf::libxdf)
target_compile_features(test_libxdf PRIVATE cxx_std_20)

enable_testing()
add_test(NAME test_libxdf COMMAND test_libxdf)
