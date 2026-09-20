cmake_minimum_required(VERSION 3.15)
project(test_notcurses C)

# Find the package via Conan-generated CMakeDeps
find_package(notcurses REQUIRED)

add_executable(test_notcurses test.c)
target_link_libraries(test_notcurses PRIVATE notcurses::notcurses)
# pty.h/openpty visibility (glibc wants _GNU_SOURCE; musl/OHOS is fine either way)
target_compile_definitions(test_notcurses PRIVATE _GNU_SOURCE)
# openpty lives in libc on musl/OHOS, in libutil on some glibc setups
include(CheckLibraryExists)
check_library_exists(util openpty "" HAVE_LIBUTIL_OPENPTY)
if(HAVE_LIBUTIL_OPENPTY)
  target_link_libraries(test_notcurses PRIVATE util)
endif()

enable_testing()
add_test(NAME test_notcurses COMMAND test_notcurses)
