cmake_minimum_required(VERSION 3.15)
project(test_sciplot CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(sciplot REQUIRED)

add_executable(test_sciplot test.cpp)
target_link_libraries(test_sciplot sciplot::sciplot)

add_executable(test_ohos_special test_ohos_special.cpp)
target_link_libraries(test_ohos_special sciplot::sciplot)

enable_testing()
add_test(NAME test_sciplot COMMAND test_sciplot)
add_test(NAME test_ohos_special COMMAND test_ohos_special)
