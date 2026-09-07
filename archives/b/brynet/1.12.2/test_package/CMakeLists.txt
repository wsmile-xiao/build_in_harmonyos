cmake_minimum_required(VERSION 3.15)
project(test_brynet_ohos CXX)

find_package(brynet REQUIRED)

add_executable(test_brynet_ohos test_brynet_ohos.cpp)
target_link_libraries(test_brynet_ohos PRIVATE brynet::brynet)
find_package(Threads REQUIRED)
target_link_libraries(test_brynet_ohos PRIVATE Threads::Threads)
set_target_properties(test_brynet_ohos PROPERTIES CXX_STANDARD 17)
