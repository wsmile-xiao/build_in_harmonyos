cmake_minimum_required(VERSION 3.15)
project(libunwind_consumer C)

find_package(libunwind CONFIG REQUIRED)

add_executable(libunwind_consumer test_libunwind.c)
target_link_libraries(libunwind_consumer PRIVATE libunwind::libunwind)
target_compile_definitions(libunwind_consumer PRIVATE UNW_LOCAL_ONLY)

if(CMAKE_C_COMPILER_ID MATCHES "Clang|GNU")
  target_compile_options(
    libunwind_consumer
    PRIVATE
      -Wall
      -Wextra
      -Werror
      -fno-omit-frame-pointer
      -funwind-tables
  )
endif()

if(CMAKE_C_COMPILER_ID MATCHES "Clang")
  target_compile_options(
    libunwind_consumer
    PRIVATE
      -Wno-error=unused-command-line-argument
  )
endif()
