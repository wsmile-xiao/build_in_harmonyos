cmake_minimum_required(VERSION 3.15)
project(test_libido3 C)

find_package(PkgConfig REQUIRED)

# Consume the installed libido3-0.1.pc (Requires: gtk+-3.0 propagates the
# transitive pango/gdk-pixbuf include/lib paths through pkg_check_modules,
# avoiding the CMakeDeps component-header breakage — E216).
pkg_check_modules(LIBIDO3 REQUIRED libido3-0.1 IMPORTED_TARGET)

add_executable(test_libido3 test.c)
target_include_directories(test_libido3 PRIVATE ${LIBIDO3_INCLUDE_DIRS})
target_link_directories(test_libido3 PRIVATE ${LIBIDO3_LIBRARY_DIRS})
target_link_libraries(test_libido3 PRIVATE ${LIBIDO3_LIBRARIES})
target_compile_options(test_libido3 PRIVATE ${LIBIDO3_CFLAGS_OTHER})
