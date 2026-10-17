cmake_minimum_required(VERSION 3.15)
project(test_tigr C)

# Find the package via Conan-generated CMakeDeps
find_package(tigr REQUIRED)

add_executable(test_tigr test_tigr.c)
target_link_libraries(test_tigr tigr::tigr)

add_executable(test_tigr_ohos test_tigr_ohos.c)
target_link_libraries(test_tigr_ohos tigr::tigr)

enable_testing()
add_test(NAME test_tigr COMMAND test_tigr)
add_test(NAME test_tigr_ohos COMMAND test_tigr_ohos)
