cmake_minimum_required(VERSION 3.15)
project(test_geocode_glib C)

# CMakeDeps target (NOT pkg_check_modules): the pkg-config route pulls
# glib-2.0.pc's full recursive Libs line into the link command, and the
# `-l:ld-musl-aarch64.so.1` entry gets mangled by cmake's link flag
# splitting on this host (ld.lld: "unable to find library
# -l:ld-musl-aarch64.so.1" even though /lib/ld-musl-aarch64.so.1 exists —
# manual clang linking with the same flags works). The CMakeDeps target
# links the libraries directly without the pc Libs passthrough
# (gtksourceview5 / libshumate test_package precedent).
find_package(geocode-glib-2.0 REQUIRED CONFIG)
find_package(glib REQUIRED)

add_executable(test_geocode_glib test.c)
target_link_libraries(test_geocode_glib geocode-glib-2.0::geocode-glib-2.0 glib::glib)
target_compile_definitions(test_geocode_glib PRIVATE VERSION="3.26.4")

if(CMAKE_C_COMPILER_ID MATCHES "Clang|GNU")
    target_link_options(test_geocode_glib PRIVATE "-Wl,-rpath,$ORIGIN" "-Wl,--disable-new-dtags")
endif()

enable_testing()
add_test(NAME test_geocode_glib COMMAND $<TARGET_FILE:test_geocode_glib>)
