cmake_minimum_required(VERSION 3.15)
project(test_syrep CXX)

find_package(syrep REQUIRED)

add_executable(test_syrep test_syrep.cpp)
# syrep is an application package: bring its bin dir into PATH via conanrun env
target_link_libraries(test_syrep syrep::syrep)

enable_testing()
add_test(NAME test_syrep COMMAND test_syrep)
