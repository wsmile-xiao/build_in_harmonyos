cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(pycxx REQUIRED)

add_executable(test_pycxx test_pycxx.cxx)
target_include_directories(test_pycxx PRIVATE ${pycxx_INCLUDE_DIRS} ${pycxx_INCLUDE_DIRS}/CXX)

enable_testing()
add_test(NAME test_pycxx COMMAND test_pycxx)
