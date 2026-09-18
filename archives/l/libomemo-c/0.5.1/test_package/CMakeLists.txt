cmake_minimum_required(VERSION 3.15)
project(test_libomemo-c C)

find_package(libomemo-c REQUIRED)

add_executable(test_libomemo-c test.c)
target_link_libraries(test_libomemo-c PRIVATE libomemo-c::libomemo-c)
# On OHOS libm is part of libc; do not link separate m (would cause 'No rule to make target m' with Make)
if(NOT CMAKE_SYSTEM_NAME STREQUAL "OHOS")
  find_library(M_LIB m)
  if(M_LIB)
    target_link_libraries(test_libomemo-c PRIVATE ${M_LIB})
  endif()
endif()

enable_testing()
add_test(NAME test_libomemo-c COMMAND test_libomemo-c)
