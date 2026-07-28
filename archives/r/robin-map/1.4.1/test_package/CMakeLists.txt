cmake_minimum_required(VERSION 3.13)
project(robinmap_test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Must match Homebrew / nanobind: package name tsl-robin-map, target tsl::robin_map
find_package(tsl-robin-map REQUIRED)

add_executable(robinmap_test main.cpp)
target_link_libraries(robinmap_test PRIVATE tsl::robin_map)

if(ROBIN_MAP_OHOS_TEST)
    target_link_options(robinmap_test PRIVATE -static)
endif()
