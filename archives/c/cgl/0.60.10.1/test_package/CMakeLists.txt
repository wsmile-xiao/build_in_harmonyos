cmake_minimum_required(VERSION 3.15)
project(test_cgl LANGUAGES CXX)

find_package(cgl CONFIG REQUIRED)
add_executable(test_cgl test.cpp)
target_link_libraries(test_cgl PRIVATE cgl::cgl)

# HarmonyOS special test: exercises the CglLandP public API.
add_executable(landp_ohos_test landp_ohos_test.cpp)
target_link_libraries(landp_ohos_test PRIVATE cgl::cgl)

# Consumer use case: third-party app using only installed public headers/API.
add_executable(landp_consumer landp_consumer.cpp)
target_link_libraries(landp_consumer PRIVATE cgl::cgl)

enable_testing()
add_test(NAME cgl_smoke COMMAND test_cgl)
add_test(NAME landp_ohos COMMAND landp_ohos_test)
add_test(NAME landp_consumer COMMAND landp_consumer)
