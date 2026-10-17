cmake_minimum_required(VERSION 3.15)
project(test_modplug C)

# Consume the FINAL Conan package via CMakeDeps: find_package(libmodplug)
# resolves the generated libmodplug-config.cmake. Headers install to
# include/libmodplug/ (src/Makefile.am libmodpluginclude_HEADERS), so
# <libmodplug/modplug.h> resolves through the target's
# INTERFACE_INCLUDE_DIRECTORIES alone. libmodplug is a C++ implementation
# exposed through a C API; the test compiles as plain C to prove the
# public header is C-consumable, and CMakeDeps links the C++ runtime
# implicitly.
find_package(libmodplug REQUIRED)

add_executable(test_modplug test_modplug.c)
target_link_libraries(test_modplug PRIVATE libmodplug::libmodplug)
target_compile_features(test_modplug PRIVATE c_std_99)
