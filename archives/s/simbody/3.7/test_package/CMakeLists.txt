cmake_minimum_required(VERSION 3.15)
project(test_simbody CXX)

find_package(Simbody REQUIRED)

add_executable(test_simbody test.cpp)
# Simbody installs its public headers under <prefix>/include/simbody (Simbody.h
# lives at <prefix>/include/simbody/Simbody.h and internal cross-library includes
# such as "SimTKcommon/internal/common.h" resolve relative to that root). The
# Conan recipe exposes both <prefix>/include/simbody and <prefix>/include via
# cpp_info.includedirs, so Simbody::Simbody carries the correct include dirs.
target_link_libraries(test_simbody PRIVATE Simbody::Simbody)
target_compile_features(test_simbody PRIVATE cxx_std_11)

# Ensure RPATH handling for OHOS
set_target_properties(test_simbody PROPERTIES
    BUILD_RPATH_USE_ORIGIN TRUE
    INSTALL_RPATH_USE_LINK_PATH TRUE
)
