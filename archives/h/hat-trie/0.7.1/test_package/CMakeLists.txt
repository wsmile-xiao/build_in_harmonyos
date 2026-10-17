cmake_minimum_required(VERSION 3.15)
project(hat_trie_test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(tsl-hat-trie CONFIG REQUIRED)

add_executable(hat_trie_test test_hat_trie.cpp)
target_link_libraries(hat_trie_test PRIVATE tsl::hat_trie)

enable_testing()
add_test(NAME hat_trie_test COMMAND hat_trie_test)
