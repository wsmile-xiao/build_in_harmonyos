cmake_minimum_required(VERSION 3.22)
project(test_filament CXX)

# Filament requires C++20 (CMakeLists.txt:398,408 -> -std=c++20).
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# FILAMENT_PKG_DIR is injected by this test_package's conanfile from the
# resolved dependency's package_folder — the layout of a generic Conan package
# would put the archive one directory deeper, so the absolute path is passed
# explicitly rather than guessed.
if(NOT DEFINED FILAMENT_PKG_DIR)
  message(FATAL_ERROR "FILAMENT_PKG_DIR must be defined by the test_package conanfile")
endif()
if(NOT DEFINED FILAMENT_PKG_LIBDIR)
  message(FATAL_ERROR "FILAMENT_PKG_LIBDIR must be defined by the test_package conanfile")
endif()

set(FILAMENT_INCLUDE_DIR "${FILAMENT_PKG_DIR}/include")
# Absolute path of the recipe's cpp_info.libdir.  Filament installs its archives
# to `lib/${DIST_DIR}` (aarch64 here), not to `lib/`, so this is passed in rather
# than guessed.
set(FILAMENT_LIB_DIR "${FILAMENT_PKG_LIBDIR}")

if(NOT EXISTS "${FILAMENT_INCLUDE_DIR}/filament/Engine.h")
  message(FATAL_ERROR "filament/Engine.h not found under ${FILAMENT_INCLUDE_DIR}")
endif()

# Filament installs ~39 static component archives (filament, backend, filabridge,
# filaflat, math, utils, ...).  The package declares the main one in cpp_info,
# so collect them all here and link them as a group to resolve the internal
# dependency cycle-free ordering without hard-coding the list.
file(GLOB FILAMENT_ARCHIVES "${FILAMENT_LIB_DIR}/*.a")
if(NOT FILAMENT_ARCHIVES)
  message(FATAL_ERROR "no static archives found under ${FILAMENT_LIB_DIR}")
endif()
list(LENGTH FILAMENT_ARCHIVES FILAMENT_ARCHIVE_COUNT)
message(STATUS "filament: linking ${FILAMENT_ARCHIVE_COUNT} component archives")

add_executable(test_filament test_filament.cpp)
target_include_directories(test_filament PRIVATE
  "${FILAMENT_INCLUDE_DIR}"
  "${FILAMENT_INCLUDE_DIR}/filament"   # for <backend/DriverEnums.h>
)
target_link_libraries(test_filament PRIVATE
  -Wl,--start-group ${FILAMENT_ARCHIVES} -Wl,--end-group
)

enable_testing()
add_test(NAME test_filament COMMAND test_filament)
