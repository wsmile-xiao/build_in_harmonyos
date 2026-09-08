cmake_minimum_required(VERSION 3.15)
project(test_optional_lite CXX)

find_package(optional-lite REQUIRED)

# C++17 consumer: default integration mode (nonstd::optional selects std::optional on C++17)
add_executable(test_optional_lite test_optional_lite.cpp)
target_link_libraries(test_optional_lite PRIVATE nonstd::optional-lite)
set_target_properties(test_optional_lite PROPERTIES CXX_STANDARD 17)

# C++14 consumer: nonstd backport implementation, covers the new value_or_eval()
# extension API introduced in 3.6.0
add_executable(test_optional_lite_ext test_optional_lite_ext.cpp)
target_link_libraries(test_optional_lite_ext PRIVATE nonstd::optional-lite)
set_target_properties(test_optional_lite_ext PROPERTIES CXX_STANDARD 14)
