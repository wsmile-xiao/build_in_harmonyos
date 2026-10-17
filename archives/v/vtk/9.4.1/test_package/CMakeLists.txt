cmake_minimum_required(VERSION 3.15)
project(test_vtk CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps.
# VTK exposes the VTK:: namespace (e.g. VTK::CommonCore for vtkNew,
# VTK::FiltersSources for vtkSphereSource).  Note: the COMPONENT names are
# the bare module names (CommonCore, FiltersSources), NOT the VTK:: target
# names — VTK's vtk-config.cmake maps COMPONENTS to VTK::* imported targets.
find_package(VTK REQUIRED COMPONENTS CommonCore FiltersSources)

# ── OHOS musl dynamic linker workaround ──────────────────────────────
# The OHOS musl linker does NOT honor LD_LIBRARY_PATH — it only searches
# the fixed paths in /etc/ld-musl-aarch64.path (system dirs), which does
# not include the Conan package cache.  Without an embedded RPATH the test
# binary cannot locate the ~150 VTK shared libraries at runtime.  Derive
# the VTK lib directory from VTK_DIR (lib/cmake/vtk-9.4 → lib) and embed it
# as a build-tree RPATH so the test binary links at runtime.
get_filename_component(_vtk_lib_dir "${VTK_DIR}/../.." ABSOLUTE)
set(CMAKE_SKIP_RPATH OFF)
set(CMAKE_BUILD_WITH_INSTALL_RPATH ON)
set(CMAKE_INSTALL_RPATH "${_vtk_lib_dir}")

add_executable(test_vtk src/main.cpp)
target_link_libraries(test_vtk PRIVATE VTK::CommonCore VTK::FiltersSources)
# Force the RPATH onto the test binary (some toolchains strip build rpath)
set_target_properties(test_vtk PROPERTIES
    BUILD_RPATH "${_vtk_lib_dir}"
    INSTALL_RPATH "${_vtk_lib_dir}")

enable_testing()
add_test(NAME test_vtk COMMAND test_vtk)
