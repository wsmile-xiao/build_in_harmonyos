cmake_minimum_required(VERSION 3.15)
project(test_config-loader CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(config-loader REQUIRED)
find_package(tinyxml2 CONFIG REQUIRED)
find_package(JsonCpp CONFIG REQUIRED)
find_package(yaml-cpp CONFIG REQUIRED)

set(CL_DEP_LIBS config-loader::config-loader tinyxml2::tinyxml2 JsonCpp::JsonCpp yaml-cpp::yaml-cpp)

add_executable(test_config-loader test_config-loader.cpp)
target_link_libraries(test_config-loader ${CL_DEP_LIBS})

# HarmonyOS platform-specific test (independent from consumer test)
add_executable(ohos_platform_test ohos_platform_test.cpp)
target_link_libraries(ohos_platform_test ${CL_DEP_LIBS})

enable_testing()
add_test(NAME test_config-loader COMMAND test_config-loader)
add_test(NAME ohos_platform_test COMMAND ohos_platform_test)
