cmake_minimum_required(VERSION 3.15)
project(test_kitemmodels CXX)

find_package(KF6ItemModels REQUIRED)

add_executable(test_kitemmodels test.cpp)
target_link_libraries(test_kitemmodels KF6::ItemModels)

enable_testing()
add_test(NAME test_kitemmodels COMMAND test_kitemmodels)
