cmake_minimum_required(VERSION 3.15)
project(test_libicns C)

# Find the package via Conan-generated CMakeDeps
find_package(libicns REQUIRED)

add_executable(test_libicns test.c)
target_link_libraries(test_libicns PRIVATE libicns::libicns)

if(CMAKE_SYSTEM_NAME MATCHES "HarmonyOS|OHOS")
  add_executable(test_ohos_libicns test_ohos_libicns.c)
  target_link_libraries(test_ohos_libicns PRIVATE libicns::libicns)
endif()

enable_testing()
add_test(NAME test_libicns COMMAND test_libicns)