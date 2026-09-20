cmake_minimum_required(VERSION 3.16)
project(test_kleidiai LANGUAGES CXX)

find_package(KleidiAI CONFIG REQUIRED)

add_executable(test_kleidiai test_kleidiai.cpp)
target_compile_features(test_kleidiai PRIVATE cxx_std_17)
target_link_libraries(test_kleidiai PRIVATE KleidiAI::kleidiai)
