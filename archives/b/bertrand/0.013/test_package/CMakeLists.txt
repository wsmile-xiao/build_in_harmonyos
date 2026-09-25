cmake_minimum_required(VERSION 3.15)
project(test_bertrand CXX)

# Find the package via Conan-generated CMakeDeps
find_package(bertrand REQUIRED)

add_executable(test_bertrand test.cpp)
target_link_libraries(test_bertrand PRIVATE bertrand::bertrand)
target_compile_features(test_bertrand PRIVATE cxx_std_17)
# Contracts must be active at include time (same flags as upstream tests)
target_compile_definitions(test_bertrand PRIVATE
  BERTRAND_ENABLE_CONTRACTS
  BERTRAND_CONTRACTS_ARE_EXCEPTIONS)

enable_testing()
add_test(NAME test_bertrand COMMAND test_bertrand)

# OHOS 专项测试（运行时异常路径 + find::in，见 test_ohos.cpp 头部说明）
add_executable(test_ohos test_ohos.cpp)
target_link_libraries(test_ohos PRIVATE bertrand::bertrand)
target_compile_features(test_ohos PRIVATE cxx_std_17)
target_compile_definitions(test_ohos PRIVATE
  BERTRAND_ENABLE_CONTRACTS
  BERTRAND_CONTRACTS_ARE_EXCEPTIONS)
add_test(NAME test_ohos COMMAND test_ohos)