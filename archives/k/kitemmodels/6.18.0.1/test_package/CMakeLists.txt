cmake_minimum_required(VERSION 3.16)
project(test_kitemmodels CXX)

find_package(KF6ItemModels REQUIRED)
find_package(Qt6Core REQUIRED)
find_package(Qt6Qml REQUIRED)

add_executable(test_kitemmodels test.cpp)
target_link_libraries(test_kitemmodels KF6::ItemModels Qt6::Qml Qt6::Core)

enable_testing()
add_test(NAME test_kitemmodels COMMAND test_kitemmodels)
