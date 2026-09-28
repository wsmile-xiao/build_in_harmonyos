cmake_minimum_required(VERSION 3.15)
project(test_ptscotch C)

# Find the package via the Conan-generated CMakeDeps config
# (cmake_file_name = "ptscotch", from conanfile.py package_info).
find_package(ptscotch REQUIRED)

add_executable(test_ptscotch test.c)

# MPI comes in transitively: the PT-SCOTCH package declares its MPI
# dependency, so the generated target carries MPI::MPI_C in its interface
# (providing both mpi.h and libmpi). Linking the library target is therefore
# enough -- no separate find_package(MPI) is needed, which matters because
# CMake's own FindMPI cannot resolve the MPI wrappers on OHOS.
target_link_libraries(test_ptscotch PRIVATE ptscotch::ptscotch)
