cmake_minimum_required(VERSION 3.16)
project(test_kpackage LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Qt6 REQUIRED COMPONENTS Core)
find_package(KF6Package CONFIG REQUIRED)

add_executable(test_kpackage test.cpp)
target_link_libraries(test_kpackage PRIVATE Qt6::Core KF6::Package)

add_executable(test_ohos_adaptation test_ohos_adaptation.cpp)
target_link_libraries(test_ohos_adaptation PRIVATE Qt6::Core KF6::Package)

enable_testing()
add_test(NAME test_kpackage COMMAND test_kpackage)
add_test(NAME test_ohos_adaptation COMMAND test_ohos_adaptation)
