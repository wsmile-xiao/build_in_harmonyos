cmake_minimum_required(VERSION 3.16)
project(qtbase_dependency_preflight LANGUAGES CXX)
find_package(Threads REQUIRED)
add_library(qtbase_dependency_probe SHARED dependency_probe.cpp)
set_target_properties(qtbase_dependency_probe PROPERTIES SUFFIX ".so.1" INSTALL_RPATH "$ORIGIN")
target_compile_features(qtbase_dependency_probe PRIVATE cxx_std_17)
target_link_options(qtbase_dependency_probe PRIVATE -Wl,--no-undefined)
target_include_directories(qtbase_dependency_probe PRIVATE
    "${DBUS_INCLUDE}" "${EXPAT_INCLUDE}" "${OPENSSL_INCLUDE}" "${XKB_INCLUDE}" "${WAYLAND_INCLUDE}")
target_link_libraries(qtbase_dependency_probe PRIVATE
    "${DBUS_LIBRARY}" "${EXPAT_LIBRARY}" "${SSL_LIBRARY}" "${CRYPTO_LIBRARY}" "${XKB_LIBRARY}"
    "${WAYLAND_CLIENT}" "${WAYLAND_SERVER}" "${WAYLAND_CURSOR}" "${WAYLAND_EGL}"
    Threads::Threads ${CMAKE_DL_LIBS})
add_executable(qtbase_dependency_consumer dependency_consumer.cpp)
set_target_properties(qtbase_dependency_consumer PROPERTIES INSTALL_RPATH "$ORIGIN")
target_link_libraries(qtbase_dependency_consumer PRIVATE qtbase_dependency_probe)
install(TARGETS qtbase_dependency_probe qtbase_dependency_consumer LIBRARY DESTINATION lib RUNTIME DESTINATION lib)
