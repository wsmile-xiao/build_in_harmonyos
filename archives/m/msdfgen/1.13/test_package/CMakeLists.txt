cmake_minimum_required(VERSION 3.15)
project(test_msdfgen CXX)

# Consume the FINAL Conan package via CMakeDeps: find_package(msdfgen)
# resolves the generated msdfgen-config.cmake, which defines the
# msdfgen::msdfgen target. The target's INTERFACE_INCLUDE_DIRECTORIES
# (from the recipe's package_info includedirs) propagates the package's
# include/ on its own — <msdfgen.h> and <msdfgen-ext.h> resolve through
# target_link_libraries alone; no extra include directories are needed.
find_package(msdfgen REQUIRED)

add_executable(test_msdfgen test_msdfgen.cpp)
target_link_libraries(test_msdfgen PRIVATE msdfgen::msdfgen)
target_compile_features(test_msdfgen PRIVATE cxx_std_11)
