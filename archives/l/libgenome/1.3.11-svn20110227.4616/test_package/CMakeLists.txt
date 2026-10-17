cmake_minimum_required(VERSION 3.15)
project(libgenome_consumer LANGUAGES CXX)

find_package(libgenome CONFIG REQUIRED)
add_executable(test_libgenome test.cpp)
target_compile_features(test_libgenome PRIVATE cxx_std_11)
target_link_libraries(test_libgenome PRIVATE libgenome::libgenome)
