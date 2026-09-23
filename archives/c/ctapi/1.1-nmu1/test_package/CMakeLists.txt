cmake_minimum_required(VERSION 3.15)
project(test_ctapi LANGUAGES C CXX)

find_package(ctapi CONFIG REQUIRED)

add_library(ctapi_mock OBJECT ctapi_mock.c)
target_link_libraries(ctapi_mock PRIVATE ctapi::ctapi)

function(add_ctapi_test target)
  add_executable(${target} ${ARGN})
  target_link_libraries(${target} PRIVATE ctapi::ctapi)
  target_link_options(${target} PRIVATE -static)
endfunction()

add_ctapi_test(test_ctapi_c test_ctapi_c.c $<TARGET_OBJECTS:ctapi_mock>)
add_ctapi_test(test_ctapi_cpp test_ctapi_cpp.cpp $<TARGET_OBJECTS:ctapi_mock>)
add_ctapi_test(test_ctapi_ohos test_ctapi_ohos.c)
