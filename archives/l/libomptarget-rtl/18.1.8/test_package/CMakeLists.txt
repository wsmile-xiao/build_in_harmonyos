cmake_minimum_required(VERSION 3.20)
project(test_libomptarget_rtl C)

# llvm package uses cmake_find_mode=none (provides its own LLVMConfig.cmake).
# The RTL plugin links libLLVM, so CMakeDeps emits an llvm::llvm reference in
# the target link interface — resolve it via LLVM's own config.
find_package(LLVM REQUIRED)
if(NOT TARGET llvm::llvm)
    add_library(llvm::llvm INTERFACE IMPORTED)
    set_property(TARGET llvm::llvm PROPERTY INTERFACE_LINK_LIBRARIES LLVM)
endif()

find_package(libomptarget-rtl CONFIG REQUIRED)

add_executable(test_libomptarget_rtl test.c)
target_link_libraries(test_libomptarget_rtl PRIVATE
    libomptarget-rtl::omptarget.rtl.aarch64)
