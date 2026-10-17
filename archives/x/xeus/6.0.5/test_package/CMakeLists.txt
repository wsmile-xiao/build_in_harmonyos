cmake_minimum_required(VERSION 3.16)
project(test_xeus_consumer CXX)

find_package(xeus REQUIRED CONFIG)

# Test 1: Consumer test - link xeus and use API
add_executable(test_xeus_consumer test_xeus_consumer.cpp)
target_link_libraries(test_xeus_consumer PRIVATE xeus::xeus)
target_compile_features(test_xeus_consumer PRIVATE cxx_std_17)

# Test 2: OHOS consumer test - verify type usability
add_executable(test_ohos_xeus test_ohos_xeus.cpp)
target_link_libraries(test_ohos_xeus PRIVATE xeus::xeus)
target_compile_features(test_ohos_xeus PRIVATE cxx_std_17)
