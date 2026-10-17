cmake_minimum_required(VERSION 3.16)
project(pimcommon_test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(KPim6PimCommon 6.6.3 CONFIG REQUIRED)

add_executable(test_pimcommon test_pimcommon.cpp)
target_link_libraries(test_pimcommon PRIVATE KPim6::PimCommon)

enable_testing()
add_test(NAME pimcommon_consumer_test COMMAND test_pimcommon)
