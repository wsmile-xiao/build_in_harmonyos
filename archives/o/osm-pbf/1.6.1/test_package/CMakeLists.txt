cmake_minimum_required(VERSION 3.15)
project(test_osmpbf CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Protobuf/abseil from cmd-pkgs prefix (do not clobber Conan generators path)
if(OHOS_DEPS_PREFIX)
  list(APPEND CMAKE_PREFIX_PATH "${OHOS_DEPS_PREFIX}")
endif()

find_package(osmpbf REQUIRED)
find_package(Protobuf REQUIRED)

add_executable(test_osmpbf test.cpp)
target_link_libraries(test_osmpbf PRIVATE osmpbf::osmpbf protobuf::libprotobuf)

enable_testing()
add_test(NAME test_osmpbf COMMAND test_osmpbf)
