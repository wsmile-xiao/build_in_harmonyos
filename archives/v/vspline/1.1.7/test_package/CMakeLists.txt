cmake_minimum_required(VERSION 3.15)
project(test_vspline CXX)

# Find the package via Conan-generated CMakeDeps
find_package(vspline REQUIRED)
find_package(Vigra REQUIRED)

add_executable(test_vspline test_vspline.cpp)
target_link_libraries(test_vspline vspline::vspline)
target_compile_features(test_vspline PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_vspline COMMAND test_vspline)
