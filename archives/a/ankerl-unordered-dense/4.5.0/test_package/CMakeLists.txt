cmake_minimum_required(VERSION 3.15)
project(test_ankerl_unordered_dense CXX)

# Find the package via Conan-generated CMakeDeps
# (cmake_file_name=unordered_dense, target=unordered_dense::unordered_dense)
find_package(unordered_dense REQUIRED)

add_executable(test_ankerl_unordered_dense test.cpp)
target_link_libraries(test_ankerl_unordered_dense PRIVATE unordered_dense::unordered_dense)
target_compile_features(test_ankerl_unordered_dense PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_ankerl_unordered_dense COMMAND test_ankerl_unordered_dense)
