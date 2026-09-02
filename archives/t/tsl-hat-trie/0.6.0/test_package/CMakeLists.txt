cmake_minimum_required(VERSION 3.15)
project(test_tsl_hat_trie CXX)

# Find the package via Conan-generated CMakeDeps
find_package(tsl_hat_trie REQUIRED)

add_executable(test_tsl_hat_trie test.cpp)
target_link_libraries(test_tsl_hat_trie tsl::hat_trie)
target_compile_features(test_tsl_hat_trie PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_tsl_hat_trie COMMAND test_tsl_hat_trie)
