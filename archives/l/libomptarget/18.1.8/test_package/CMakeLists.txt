cmake_minimum_required(VERSION 3.20)
project(test_libomptarget C)

# Enable OpenMP (libomp drives the host-fallback target-region workflow).
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fopenmp")

# libomptarget.so cannot be loaded at process start on OHOS musl (loader
# EACCES on verneed imports from libLLVM — documented platform limit), so
# the binary must NOT hard-DT_NEEDED it. It is instead:
#   - linked at build time below (find_package + target validates the
#     package integrates, R34), dropped from DT_NEEDED by --as-needed
#   - loaded at runtime via dlopen()/dlsym() in test.c (API probe)
find_package(LLVM REQUIRED)
if(NOT TARGET llvm::llvm)
    add_library(llvm::llvm INTERFACE IMPORTED)
endif()

find_package(libomptarget CONFIG REQUIRED)

add_executable(test_libomptarget test.c)
target_link_options(test_libomptarget PRIVATE "-Wl,--as-needed")
target_link_libraries(test_libomptarget PRIVATE
    libomptarget::omptarget
    LLVM
    ${CMAKE_DL_LIBS})