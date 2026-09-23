cmake_minimum_required(VERSION 3.15)
project(test_zxing_cpp LANGUAGES CXX)

find_package(ZXing CONFIG REQUIRED)

add_executable(test_zxing_cpp test.cpp)
target_compile_features(test_zxing_cpp PRIVATE cxx_std_17)
target_link_libraries(test_zxing_cpp PRIVATE ZXing::ZXing)

enable_testing()
add_test(NAME test_zxing_cpp COMMAND test_zxing_cpp)
