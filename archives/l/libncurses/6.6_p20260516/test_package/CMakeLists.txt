cmake_minimum_required(VERSION 3.16)
project(libncurses_consumer_tests LANGUAGES C)

if(NOT DEFINED LIBNCURSES_PACKAGE_ROOT)
  message(FATAL_ERROR "LIBNCURSES_PACKAGE_ROOT must point at the Conan package")
endif()
get_filename_component(LIBNCURSES_PACKAGE_ROOT "${LIBNCURSES_PACKAGE_ROOT}" REALPATH)

find_package(libncurses CONFIG REQUIRED)

add_executable(test_curses_module src/test_curses_module.c)
target_link_libraries(test_curses_module PRIVATE libncurses::libncurses)

add_executable(test_ncurses_components src/test_ncurses_components.c)
target_link_libraries(test_ncurses_components PRIVATE libncurses::libncurses)

add_executable(test_ohos_platform src/test_ohos_platform.c)
target_link_libraries(test_ohos_platform PRIVATE libncurses::libncurses)

# Upstream CMake module contract: find_package(Curses) must resolve to the
# packaged ncurses and never to another installation on the build host.
list(PREPEND CMAKE_PREFIX_PATH "${LIBNCURSES_PACKAGE_ROOT}")
set(CURSES_NEED_NCURSES TRUE)
find_package(Curses REQUIRED)
if(NOT CURSES_INCLUDE_DIRS OR NOT CURSES_LIBRARIES)
  message(FATAL_ERROR "FindCurses resolved no include directory or library")
endif()

foreach(_directory IN LISTS CURSES_INCLUDE_DIRS)
  get_filename_component(_resolved "${_directory}" REALPATH)
  string(FIND "${_resolved}" "${LIBNCURSES_PACKAGE_ROOT}" _position)
  if(NOT _position EQUAL 0)
    message(FATAL_ERROR "FindCurses include directory outside the package: ${_resolved}")
  endif()
endforeach()
foreach(_library IN LISTS CURSES_LIBRARIES)
  if(_library MATCHES "\\.[a-zA-Z0-9]+$")
    get_filename_component(_resolved "${_library}" REALPATH)
    string(FIND "${_resolved}" "${LIBNCURSES_PACKAGE_ROOT}" _position)
    if(NOT _position EQUAL 0)
      message(FATAL_ERROR "FindCurses library outside the package: ${_resolved}")
    endif()
  endif()
endforeach()

add_executable(test_find_curses_module src/test_curses_module.c)
target_include_directories(test_find_curses_module PRIVATE ${CURSES_INCLUDE_DIRS})
target_link_libraries(test_find_curses_module PRIVATE ${CURSES_LIBRARIES})
