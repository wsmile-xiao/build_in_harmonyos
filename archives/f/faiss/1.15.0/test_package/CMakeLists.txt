cmake_minimum_required(VERSION 3.16)
project(test_faiss CXX)

find_package(faiss CONFIG REQUIRED)

add_executable(test_faiss test_faiss.cpp)
target_link_libraries(test_faiss PRIVATE faiss::faiss)

enable_testing()
add_test(NAME test_faiss COMMAND test_faiss)
