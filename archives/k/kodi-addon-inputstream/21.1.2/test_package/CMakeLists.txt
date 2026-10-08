cmake_minimum_required(VERSION 3.15)
project(test_kodi_addon_inputstream LANGUAGES CXX)

# Resolve through Conan CMakeDeps, same as any downstream Kodi deployment
# tooling; cmake_file_name is "kodi-addon-inputstream".
find_package(kodi-addon-inputstream CONFIG REQUIRED)

add_executable(test_kodi_addon_inputstream test_kodi_addon_inputstream.cpp)
target_compile_features(test_kodi_addon_inputstream PRIVATE cxx_std_17)
target_link_libraries(test_kodi_addon_inputstream PRIVATE ${CMAKE_DL_LIBS})

enable_testing()
# The test dlopen()s both packaged modules by absolute path (argv) — the
# standard way a Kodi host loads binary add-ons and their helper modules.
add_test(NAME kodi_addon_inputstream_module_contract
         COMMAND test_kodi_addon_inputstream
                 ${ADDON_LIB_DIR}/inputstream.adaptive.so
                 ${ADDON_LIB_DIR}/ssd_wv.so)
