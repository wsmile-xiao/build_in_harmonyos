cmake_minimum_required(VERSION 3.15)
project(test_smhasher CXX)

set(CMAKE_CXX_STANDARD 11)

find_package(smhasher REQUIRED)

add_executable(test_vectors test_vectors.cpp)
target_link_libraries(test_vectors smhasher::smhasher)

add_executable(test_hashes test_hashes.cpp)
target_link_libraries(test_hashes smhasher::smhasher)

enable_testing()
add_test(NAME test_vectors COMMAND test_vectors)
add_test(NAME test_hashes COMMAND test_hashes)
