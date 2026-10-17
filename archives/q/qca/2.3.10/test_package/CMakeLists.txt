cmake_minimum_required(VERSION 3.16)
project(test_qca CXX)

find_package(Qt6 REQUIRED CONFIG COMPONENTS Core Core5Compat)

add_executable(test_qca test_qca.cpp)
target_include_directories(test_qca PRIVATE ${QCA_INCLUDE_DIR})
target_link_directories(test_qca PRIVATE ${QCA_LIBRARY_DIR})
target_link_libraries(test_qca PRIVATE qca-qt6 Qt6::Core Qt6::Core5Compat)
target_compile_features(test_qca PRIVATE cxx_std_17)
