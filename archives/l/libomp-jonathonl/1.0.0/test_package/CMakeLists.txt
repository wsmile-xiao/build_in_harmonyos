cmake_minimum_required(VERSION 3.15)
project(test_libomp_jonathonl LANGUAGES CXX)

find_package(libomp-jonathonl REQUIRED CONFIG)

add_executable(test_upstream upstream_test.cpp)
target_compile_features(test_upstream PRIVATE cxx_std_11)
target_link_libraries(test_upstream PRIVATE libomp-jonathonl::libomp-jonathonl)

enable_testing()
add_test(NAME upstream_main COMMAND test_upstream)

if(LIBOMP_JONATHONL_TEST_OHOS)
  add_executable(test_ohos_threads ohos_thread_test.cpp)
  target_compile_features(test_ohos_threads PRIVATE cxx_std_11)
  target_link_libraries(test_ohos_threads PRIVATE libomp-jonathonl::libomp-jonathonl)
  add_test(NAME ohos_thread_runtime COMMAND test_ohos_threads)
endif()
