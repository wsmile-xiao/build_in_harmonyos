cmake_minimum_required(VERSION 3.15)
project(test_effolkronium_random CXX)

# Find the package via Conan-generated CMakeDeps
# (cmake_file_name=effolkronium_random, target=effolkronium_random::effolkronium_random)
find_package(effolkronium_random REQUIRED)

add_executable(test_effolkronium_random test.cpp)
target_link_libraries(test_effolkronium_random PRIVATE effolkronium_random::effolkronium_random)
target_compile_features(test_effolkronium_random PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_effolkronium_random COMMAND test_effolkronium_random)
