cmake_minimum_required(VERSION 3.15)
project(test_xgboost C CXX)

# Find the package via Conan-generated CMakeDeps
find_package(xgboost REQUIRED)

# OpenMP is only used when xgboost was built with it (non-OHOS).
# On OHOS (CMAKE_SYSTEM_NAME=HarmonyOS), xgboost is built with
# USE_OPENMP=OFF, so skip OpenMP dependency entirely.
if(NOT CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
  find_package(OpenMP QUIET)
endif()

add_executable(test_xgboost test.c)
if(OpenMP_CXX_FOUND)
  target_link_libraries(test_xgboost xgboost::xgboost c++ OpenMP::OpenMP_CXX)
else()
  target_link_libraries(test_xgboost xgboost::xgboost c++)
endif()

enable_testing()
add_test(NAME test_xgboost COMMAND test_xgboost)
