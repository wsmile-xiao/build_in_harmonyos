cmake_minimum_required(VERSION 3.15)
project(paryfor_test_package LANGUAGES CXX)

find_package(paryfor CONFIG REQUIRED)
find_package(Threads REQUIRED)

add_executable(test_paryfor test_paryfor.cpp)
target_link_libraries(test_paryfor PRIVATE paryfor::paryfor Threads::Threads)
set_property(TARGET test_paryfor PROPERTY CXX_STANDARD 14)
set_property(TARGET test_paryfor PROPERTY CXX_STANDARD_REQUIRED ON)

add_executable(test_paryfor_ohos test_paryfor_ohos.cpp)
target_link_libraries(test_paryfor_ohos PRIVATE paryfor::paryfor Threads::Threads)
set_property(TARGET test_paryfor_ohos PROPERTY CXX_STANDARD 14)
set_property(TARGET test_paryfor_ohos PROPERTY CXX_STANDARD_REQUIRED ON)
