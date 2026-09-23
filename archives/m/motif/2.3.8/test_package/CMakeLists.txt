cmake_minimum_required(VERSION 3.15)
project(test_motif C)

# Find the package via Conan-generated CMakeDeps (cmake_file_name = "motif").
find_package(motif REQUIRED)

# test_motif.c calls the XmString API exported by libXm.so.4 and dlopen()s the
# packaged SONAME. libXm is exposed as the target motif::motif.
add_executable(test_motif test_motif.c)
target_link_libraries(test_motif motif::motif)

enable_testing()
add_test(NAME test_motif COMMAND test_motif)
