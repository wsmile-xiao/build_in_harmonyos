cmake_minimum_required(VERSION 3.15)
project(test_jose C)

find_package(jose CONFIG REQUIRED)

add_executable(test_jose test_jose.c)
target_link_libraries(test_jose PRIVATE jose::jose)
# HMBS OHOS loader ignores LD_LIBRARY_PATH/LD_PRELOAD: enforce RUNPATH at
# the CMake target level (immune to Conan toolchain-cache overrides of
# CMAKE_INSTALL_RPATH/LDFLAGS). Absolute dep dirs arrive via TEST_RPATH_DIRS;
# $ORIGIN entries resolve the exe-dir copies staged by conanfile.py.
if(DEFINED TEST_RPATH_DIRS AND NOT "${TEST_RPATH_DIRS}" STREQUAL "")
  set_target_properties(test_jose PROPERTIES
    INSTALL_RPATH "${TEST_RPATH_DIRS};$ORIGIN;$ORIGIN/../lib"
    BUILD_WITH_INSTALL_RPATH TRUE
    INSTALL_RPATH_USE_LINK_PATH TRUE
    SKIP_BUILD_RPATH FALSE)
else()
  set_target_properties(test_jose PROPERTIES
    INSTALL_RPATH "$ORIGIN;$ORIGIN/../lib"
    BUILD_WITH_INSTALL_RPATH TRUE
    INSTALL_RPATH_USE_LINK_PATH TRUE
    SKIP_BUILD_RPATH FALSE)
endif()
# Round-6 belt-and-suspenders: emit DT_RUNPATH as raw linker flags as well,
# so the loader sees it even if any CMake RPATH machinery is neutralized by the
# toolchain file. Upstream meson build-tree binaries (25/25 passed) prove
# the device loader honors embedded runpaths; only the landing was in doubt.
if(DEFINED TEST_RPATH_DIRS AND NOT "${TEST_RPATH_DIRS}" STREQUAL "")
  foreach(_d ${TEST_RPATH_DIRS})
    target_link_options(test_jose PRIVATE "LINKER:-rpath,${_d}")
  endforeach()
endif()
target_link_options(test_jose PRIVATE "LINKER:-rpath,$ORIGIN" "LINKER:-rpath,$ORIGIN/../lib")
