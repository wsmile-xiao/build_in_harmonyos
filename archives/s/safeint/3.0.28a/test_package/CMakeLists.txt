cmake_minimum_required(VERSION 3.15)
project(test_safeint LANGUAGES C CXX)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(safeint CONFIG REQUIRED)

add_executable(test_safeint test_safeint.cpp)
target_link_libraries(test_safeint PRIVATE safeint::safeint)

add_executable(test_safe_math test_safe_math.c)
target_link_libraries(test_safe_math PRIVATE safeint::safeint)

add_executable(test_safeint_ohos test_safeint_ohos.cpp)
target_link_libraries(test_safeint_ohos PRIVATE safeint::safeint)

enable_testing()
add_test(NAME safeint_consumer_cpp COMMAND test_safeint)
add_test(NAME safeint_consumer_c COMMAND test_safe_math)
add_test(NAME safeint_ohos_platform COMMAND test_safeint_ohos)
