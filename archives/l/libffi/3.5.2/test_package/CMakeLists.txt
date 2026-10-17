cmake_minimum_required(VERSION 3.15)
project(libffi_consumer C)

set(CMAKE_SKIP_RPATH TRUE)

find_package(libffi CONFIG REQUIRED)

add_executable(libffi_consumer test_package.c)
target_link_libraries(libffi_consumer PRIVATE libffi::libffi)
target_compile_features(libffi_consumer PRIVATE c_std_11)

if(CMAKE_SYSTEM_NAME MATCHES "HarmonyOS|OHOS|Linux")
  add_library(libffi_pic_probe SHARED test_package.c)
  target_compile_features(libffi_pic_probe PRIVATE c_std_11)
  target_link_libraries(
    libffi_pic_probe
    PRIVATE
      "-Wl,--whole-archive"
      libffi::libffi
      "-Wl,--no-whole-archive"
  )
endif()

if(CMAKE_C_COMPILER_ID MATCHES "Clang|GNU")
  target_compile_options(libffi_consumer PRIVATE -Wall -Wextra -Werror)
  if(TARGET libffi_pic_probe)
    target_compile_options(libffi_pic_probe PRIVATE -Wall -Wextra -Werror)
  endif()
endif()

if(CMAKE_C_COMPILER_ID MATCHES "Clang")
  target_compile_options(
    libffi_consumer PRIVATE -Wno-error=unused-command-line-argument
  )
  if(TARGET libffi_pic_probe)
    target_compile_options(
      libffi_pic_probe PRIVATE -Wno-error=unused-command-line-argument
    )
  endif()
endif()
