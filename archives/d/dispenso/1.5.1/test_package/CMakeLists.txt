cmake_minimum_required(VERSION 3.16)
project(test_dispenso LANGUAGES CXX)

find_package(Dispenso CONFIG REQUIRED)

add_executable(test_dispenso test.cpp)
target_compile_features(test_dispenso PRIVATE cxx_std_17)
target_link_libraries(test_dispenso PRIVATE Dispenso::dispenso)

enable_testing()
add_test(NAME dispenso_consumer_api COMMAND test_dispenso)

if(DISPENSO_TEST_OHOS)
  add_executable(test_dispenso_ohos ohos_thread_runtime.cpp)
  target_compile_features(test_dispenso_ohos PRIVATE cxx_std_17)
  target_link_libraries(test_dispenso_ohos PRIVATE Dispenso::dispenso)
  add_test(NAME dispenso_ohos_thread_runtime COMMAND test_dispenso_ohos)
endif()
