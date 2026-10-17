cmake_minimum_required(VERSION 3.15)

project(test_libelfin CXX)

find_package(libelfin CONFIG REQUIRED)

add_executable(test_libelfin test_libelfin.cc)

target_compile_features(test_libelfin PRIVATE cxx_std_11)

# The conanfile passes the e_machine value that matches settings.arch, so the
# test asserts the real target machine instead of assuming one architecture.
if(NOT DEFINED LIBELFIN_EXPECT_MACHINE)
    set(LIBELFIN_EXPECT_MACHINE 0)
endif()

target_compile_definitions(test_libelfin PRIVATE EXPECT_MACHINE=${LIBELFIN_EXPECT_MACHINE})

target_link_libraries(test_libelfin PRIVATE libelfin::libelfin)
