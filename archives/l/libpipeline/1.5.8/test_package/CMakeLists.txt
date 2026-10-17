cmake_minimum_required(VERSION 3.15)
project(test_libpipeline C)

find_package(PkgConfig REQUIRED)
# libpipeline ships lib/libpipeline.pc; Conan's PkgConfigDeps generator emits a
# self-contained .pc whose prefix points at the package folder.
pkg_check_modules(LIBPIPELINE REQUIRED libpipeline)

add_executable(test_libpipeline test_libpipeline.c)
target_include_directories(test_libpipeline PRIVATE ${LIBPIPELINE_INCLUDE_DIRS})
target_link_libraries(test_libpipeline PRIVATE ${LIBPIPELINE_LINK_LIBRARIES})

enable_testing()
add_test(NAME test_libpipeline COMMAND test_libpipeline)
