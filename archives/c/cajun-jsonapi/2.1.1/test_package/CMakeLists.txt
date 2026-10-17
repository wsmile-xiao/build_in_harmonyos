cmake_minimum_required(VERSION 3.15)
project(test_cajun_jsonapi CXX)

# Find the package via Conan-generated CMakeDeps
find_package(cajun-jsonapi REQUIRED)

add_executable(test_cajun_jsonapi test.cpp)
target_link_libraries(test_cajun_jsonapi cajun-jsonapi::cajun-jsonapi)
target_compile_features(test_cajun_jsonapi PRIVATE cxx_std_11)

# HarmonyOS/aarch64 specialty tests (UTF-8 / double precision / exceptions / nesting)
add_executable(test_ohos test_ohos.cpp)
target_link_libraries(test_ohos cajun-jsonapi::cajun-jsonapi)
target_compile_features(test_ohos PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_cajun_jsonapi COMMAND test_cajun_jsonapi)
add_test(NAME test_ohos COMMAND test_ohos)
