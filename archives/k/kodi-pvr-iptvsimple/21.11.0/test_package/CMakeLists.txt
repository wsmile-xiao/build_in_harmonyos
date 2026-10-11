cmake_minimum_required(VERSION 3.15)
project(test_kodi_pvr_iptvsimple LANGUAGES CXX)

# Resolve through Conan CMakeDeps, same as any downstream Kodi deployment
# tooling; cmake_file_name is "kodi-pvr-iptvsimple".
find_package(kodi-pvr-iptvsimple CONFIG REQUIRED)

# ADDON_MODULE is the absolute path of the packaged add-on module passed in by
# test_package/conanfile.py.
message(STATUS "add-on module under test: ${ADDON_MODULE}")

# Consumer test: links the packaged module (its internal FileUtils helpers are
# exported) and dlopen()s it exactly like the Kodi host does.
add_executable(test_kodi_pvr_iptvsimple test_kodi_pvr_iptvsimple.cpp)
target_compile_features(test_kodi_pvr_iptvsimple PRIVATE cxx_std_17)
target_link_libraries(test_kodi_pvr_iptvsimple PRIVATE
                      "${ADDON_MODULE}"
                      ${CMAKE_DL_LIBS})
# The module is linked by file name (its SONAME is "pvr.iptvsimple.so"); point
# the run-time search path at the packaged lib directory so the test binary is
# self-contained (LD_LIBRARY_PATH independent).
get_filename_component(ADDON_LIB_DIR "${ADDON_MODULE}" DIRECTORY)
set_target_properties(test_kodi_pvr_iptvsimple PROPERTIES
                      BUILD_RPATH "${ADDON_LIB_DIR}"
                      INSTALL_RPATH "${ADDON_LIB_DIR}")

# HarmonyOS-specific test (strictly compiled).
add_executable(test_kodi_pvr_iptvsimple_ohos test_ohos.cpp)
target_compile_features(test_kodi_pvr_iptvsimple_ohos PRIVATE cxx_std_17)
target_compile_options(test_kodi_pvr_iptvsimple_ohos PRIVATE -Wall -Wextra -Werror)
target_link_libraries(test_kodi_pvr_iptvsimple_ohos PRIVATE ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_kodi_pvr_iptvsimple
         COMMAND test_kodi_pvr_iptvsimple "${ADDON_MODULE}")
add_test(NAME test_kodi_pvr_iptvsimple_ohos
         COMMAND test_kodi_pvr_iptvsimple_ohos "${ADDON_MODULE}")
