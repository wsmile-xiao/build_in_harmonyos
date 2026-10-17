cmake_minimum_required(VERSION 3.16)
project(test_kdsingleapplication LANGUAGES CXX)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS Core Network)
find_package(KDSingleApplication-qt6 1.2.1 REQUIRED)

enable_testing()

add_executable(test_public_api test_public_api.cpp)
target_compile_features(test_public_api PRIVATE cxx_std_17)
target_link_libraries(test_public_api PRIVATE KDAB::kdsingleapplication Qt6::Core)
add_test(NAME test_public_api COMMAND test_public_api)

add_executable(test_harmony_ipc test_harmony_ipc.cpp)
target_compile_features(test_harmony_ipc PRIVATE cxx_std_17)
target_link_libraries(test_harmony_ipc PRIVATE KDAB::kdsingleapplication Qt6::Core)
add_test(NAME test_harmony_ipc COMMAND test_harmony_ipc)
