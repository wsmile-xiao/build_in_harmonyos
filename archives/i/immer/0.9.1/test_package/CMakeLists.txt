cmake_minimum_required(VERSION 3.15)
project(test_immer CXX)

# Find the package via Conan-generated CMakeDeps
# (cmake_file_name=Immer, target=immer)
find_package(Immer REQUIRED)

add_executable(test_immer test_immer.cpp)
target_link_libraries(test_immer PRIVATE immer)
target_compile_features(test_immer PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_immer COMMAND test_immer)
