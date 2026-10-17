cmake_minimum_required(VERSION 3.16)
project(test_libprotoc LANGUAGES CXX)

find_package(absl CONFIG REQUIRED)
find_package(Protobuf CONFIG REQUIRED)

# Consumer test: link libprotoc together with the runtime it exposes through
# the packaged CMake config, then drive the compiler library API directly.
add_executable(test_libprotoc test_libprotoc.cpp)
target_compile_features(test_libprotoc PRIVATE cxx_std_17)
target_link_libraries(test_libprotoc PRIVATE
  protobuf::libprotoc
  protobuf::libprotobuf)

# HarmonyOS-specific test: exercises libprotoc on the OHOS musl runtime
# (descriptor import, diagnostics, descriptor pool) rather than only compiling.
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS"
   OR OHOS STREQUAL "ON")
  add_executable(test_ohos_runtime test_ohos_runtime.cpp)
  target_compile_features(test_ohos_runtime PRIVATE cxx_std_17)
  target_link_libraries(test_ohos_runtime PRIVATE
    protobuf::libprotoc
    protobuf::libprotobuf)
endif()

enable_testing()
foreach(test_case descriptor pool importer diagnostics roundtrip)
  add_test(NAME libprotoc_${test_case}
           COMMAND test_libprotoc ${test_case} ${CMAKE_CURRENT_SOURCE_DIR})
endforeach()
if(TARGET test_ohos_runtime)
  add_test(NAME libprotoc_ohos_runtime
           COMMAND test_ohos_runtime ${CMAKE_CURRENT_SOURCE_DIR})
endif()
