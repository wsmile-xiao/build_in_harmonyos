cmake_minimum_required(VERSION 3.16)
project(libwnck3_consumer C)

find_package(PkgConfig REQUIRED)
pkg_check_modules(LIBWNCK REQUIRED IMPORTED_TARGET libwnck-3.0)
pkg_check_modules(X11 REQUIRED IMPORTED_TARGET x11)

add_executable(test_libwnck3 test_libwnck3.c)
target_compile_definitions(test_libwnck3 PRIVATE WNCK_I_KNOW_THIS_IS_UNSTABLE)
target_link_libraries(test_libwnck3 PRIVATE PkgConfig::LIBWNCK PkgConfig::X11)
