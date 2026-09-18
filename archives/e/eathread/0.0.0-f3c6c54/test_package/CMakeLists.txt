cmake_minimum_required(VERSION 3.15)
project(test_eathread CXX)

# Find the package via Conan-generated CMakeDeps
find_package(eathread REQUIRED)
find_package(eabase REQUIRED)

add_executable(test_eathread test_eathread.cpp)
target_link_libraries(test_eathread eathread::eathread eabase::eabase)

# HarmonyOS-specific test (distinct from the generic consumer test)
add_executable(test_eathread_ohos test_eathread_ohos.cpp)
target_link_libraries(test_eathread_ohos eathread::eathread eabase::eabase)

enable_testing()
add_test(NAME test_eathread COMMAND test_eathread)
add_test(NAME test_eathread_ohos COMMAND test_eathread_ohos)