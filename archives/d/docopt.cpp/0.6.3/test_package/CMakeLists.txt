cmake_minimum_required(VERSION 3.15)
project(test_docopt LANGUAGES CXX)

find_package(docopt CONFIG REQUIRED)

add_executable(test_docopt test.cpp test_secondary.cpp)
target_link_libraries(test_docopt PRIVATE docopt::docopt)
target_compile_features(test_docopt PRIVATE cxx_std_11)
