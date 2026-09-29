cmake_minimum_required(VERSION 3.15)
project(test_libkode LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# libkode exposes Qt types in its public headers, so the consumer also needs
# the Qt6 packages. qtbase uses cmake_find_mode=none and ships only the real
# Qt6Config.cmake; qtbase's lib/cmake is prepended via the manually written
# conan_cmakedeps_paths.cmake (audiocd/alkimia test_package precedent), so
# find_package(Qt6) resolves.
find_package(Qt6 6.0.0 CONFIG REQUIRED COMPONENTS Core Network Xml)

# libkode's static archives are consumed via plain find_path/find_library:
# the CMakeDeps-generated libkode config calls find_dependency(qtbase), which
# has no qtbaseConfig (qtbase only installs Qt6Config), so the archives are
# linked directly (audiocd test_package precedent).
find_path(LIBKODE_INCLUDE_DIR class.h
          NO_DEFAULT_PATH
          PATHS "${CONAN_LIBKODE_INCLUDE}")
find_library(LIBKODE_LIBRARY kode
             HINTS "${CONAN_LIBKODE_LIB}")
find_library(XMLSCHEMA_LIBRARY xmlschema
             HINTS "${CONAN_LIBKODE_LIB}")
find_library(XMLCOMMON_LIBRARY xmlcommon
             HINTS "${CONAN_LIBKODE_LIB}")

add_executable(test_libkode test_libkode.cpp)
target_include_directories(test_libkode PRIVATE ${LIBKODE_INCLUDE_DIR})
target_link_libraries(test_libkode PRIVATE
    Qt6::Core
    Qt6::Network
    Qt6::Xml
    ${LIBKODE_LIBRARY}
    ${XMLSCHEMA_LIBRARY}
    ${XMLCOMMON_LIBRARY}
)
