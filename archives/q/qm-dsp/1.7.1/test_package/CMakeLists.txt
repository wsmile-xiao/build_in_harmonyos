cmake_minimum_required(VERSION 3.15)
project(test_qmdsp CXX)

find_package(qm-dsp CONFIG REQUIRED)

add_executable(test_qmdsp test_qmdsp.cpp)
target_compile_features(test_qmdsp PRIVATE cxx_std_17)
target_link_libraries(test_qmdsp PRIVATE qm-dsp::qm-dsp)

enable_testing()
add_test(NAME test_qmdsp COMMAND test_qmdsp)
