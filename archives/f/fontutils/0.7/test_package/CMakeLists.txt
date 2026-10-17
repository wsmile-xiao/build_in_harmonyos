cmake_minimum_required(VERSION 3.15)
project(test_fontutils C)

find_package(fontutils REQUIRED)

find_library(FONTUTILS_STATIC_LIB NAMES fontutils libfontutils
             PATHS ${fontutils_PACKAGE_FOLDER_RELEASE}/lib
             NO_DEFAULT_PATH)
if(NOT FONTUTILS_STATIC_LIB)
  message(FATAL_ERROR "libfontutils.a not found in package")
endif()

add_executable(test_lib test_lib.c)
target_link_libraries(test_lib PRIVATE ${FONTUTILS_STATIC_LIB})

enable_testing()
add_test(NAME test_lib COMMAND test_lib)
