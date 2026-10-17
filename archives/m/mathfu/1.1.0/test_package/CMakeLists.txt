cmake_minimum_required(VERSION 3.15)
project(mathfu_test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(mathfu CONFIG REQUIRED)

add_executable(mathfu_test test.cpp)
target_link_libraries(mathfu_test PRIVATE mathfu::mathfu)

if(MATHFU_TEST_LINK_STATIC)
  # OHOS: statically link the consumer test so it executes natively on the
  # target (the SDK libc++.so is a linker script the loader cannot resolve).
  target_link_options(mathfu_test PRIVATE -static)
endif()

enable_testing()
add_test(NAME mathfu_test COMMAND mathfu_test)
