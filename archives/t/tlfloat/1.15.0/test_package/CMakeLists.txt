cmake_minimum_required(VERSION 3.16)
project(test_tlfloat C CXX)

find_package(tlfloat CONFIG REQUIRED)

add_executable(test_tlfloat test_tlfloat.cpp)
target_compile_features(test_tlfloat PRIVATE cxx_std_20)
target_link_libraries(test_tlfloat PRIVATE tlfloat::tlfloat)

add_executable(tlfloat_consumer_workflow consumer_workflow.cpp)
target_compile_features(tlfloat_consumer_workflow PRIVATE cxx_std_20)
target_link_libraries(tlfloat_consumer_workflow PRIVATE tlfloat::tlfloat)

enable_testing()
add_test(NAME test_tlfloat COMMAND test_tlfloat)
add_test(NAME tlfloat_consumer_workflow COMMAND tlfloat_consumer_workflow)
