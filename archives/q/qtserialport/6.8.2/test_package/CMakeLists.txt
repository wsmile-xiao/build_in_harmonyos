cmake_minimum_required(VERSION 3.16)
project(test_qtserialport LANGUAGES CXX)

find_package(Qt6 6.8.2 REQUIRED COMPONENTS Core SerialPort)

add_executable(test_qtserialport test_qtserialport.cpp)
target_compile_features(test_qtserialport PRIVATE cxx_std_17)
target_link_libraries(
    test_qtserialport
    PRIVATE Qt6::Core Qt6::SerialPort
)
