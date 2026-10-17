cmake_minimum_required(VERSION 3.16)
project(SignOnQt6 VERSION 8.61 LANGUAGES CXX)

# Upstream builds with qmake only (lib/SignOn/libsignon-qt.pri: TEMPLATE=lib,
# TARGET=signon-qt5, CMAKE_BASENAME=SignOnQt5). The conan qtbase package ships
# qmake but no OHOS mkspec, so this hand-written CMakeLists reproduces the qmake
# build for the Qt6 flavour: target signon-qt6 / CMake package SignOnQt6, which
# is what kaccounts-integration asks for:
#   find_package(SignOnQt6 8.55 CONFIG)   (SignOnQt${QT_MAJOR_VERSION})

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

find_package(Qt6 REQUIRED COMPONENTS Core DBus)

set(SIGNON_QT_TARGET signon-qt6)
set(SIGNON_SRC_DIR "${CMAKE_CURRENT_SOURCE_DIR}/lib/SignOn")

# libsignon-qt.pri: public_headers / private_headers / SOURCES
set(SIGNON_PUBLIC_HEADERS
    ${SIGNON_SRC_DIR}/sessiondata.h
    ${SIGNON_SRC_DIR}/identityinfo.h
    ${SIGNON_SRC_DIR}/authservice.h
    ${SIGNON_SRC_DIR}/identity.h
    ${SIGNON_SRC_DIR}/authsession.h
    ${SIGNON_SRC_DIR}/libsignoncommon.h
    ${SIGNON_SRC_DIR}/securitycontext.h
    ${SIGNON_SRC_DIR}/signon.h
    ${SIGNON_SRC_DIR}/signonerror.h
)

set(SIGNON_PRIVATE_HEADERS
    ${SIGNON_SRC_DIR}/authserviceimpl.h
    ${SIGNON_SRC_DIR}/async-dbus-proxy.h
    ${SIGNON_SRC_DIR}/authsessionimpl.h
    ${SIGNON_SRC_DIR}/connection-manager.h
    ${SIGNON_SRC_DIR}/dbusinterface.h
    ${SIGNON_SRC_DIR}/debug.h
    ${SIGNON_SRC_DIR}/identityimpl.h
    ${SIGNON_SRC_DIR}/identityinfoimpl.h
    ${SIGNON_SRC_DIR}/securitycontextpriv.h
)

set(SIGNON_SOURCES
    ${SIGNON_SRC_DIR}/identityinfo.cpp
    ${SIGNON_SRC_DIR}/async-dbus-proxy.cpp
    ${SIGNON_SRC_DIR}/authservice.cpp
    ${SIGNON_SRC_DIR}/authserviceimpl.cpp
    ${SIGNON_SRC_DIR}/authsession.cpp
    ${SIGNON_SRC_DIR}/authsessionimpl.cpp
    ${SIGNON_SRC_DIR}/connection-manager.cpp
    ${SIGNON_SRC_DIR}/dbusinterface.cpp
    ${SIGNON_SRC_DIR}/debug.cpp
    ${SIGNON_SRC_DIR}/identity.cpp
    ${SIGNON_SRC_DIR}/identityimpl.cpp
    ${SIGNON_SRC_DIR}/identityinfoimpl.cpp
    ${SIGNON_SRC_DIR}/securitycontext.cpp
)

# The conan `shared` option drives the library kind (default: static).
if(BUILD_SHARED_LIBS)
    add_library(${SIGNON_QT_TARGET} SHARED ${SIGNON_SOURCES})
else()
    add_library(${SIGNON_QT_TARGET} STATIC ${SIGNON_SOURCES})
endif()
add_library(SignOnQt6::SignOnQt6 ALIAS ${SIGNON_QT_TARGET})

target_include_directories(${SIGNON_QT_TARGET}
    PUBLIC
        # libsignon-qt.pri: INCLUDEPATH += . .. — the sources include their
        # siblings as <SignOn/xxx.h>, so lib/ (the parent of SignOn/) is the
        # include root at build time; at install time it is include/signon-qt6.
        $<BUILD_INTERFACE:${SIGNON_SRC_DIR}>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/lib>
        $<INSTALL_INTERFACE:include/signon-qt6>
)

# libsignon-qt.pri: QT += core dbus
target_link_libraries(${SIGNON_QT_TARGET} PUBLIC Qt6::Core Qt6::DBus)

# libsignon-qt.pri: DEFINES += QT_NO_CAST_TO_ASCII QT_NO_CAST_FROM_ASCII
target_compile_definitions(${SIGNON_QT_TARGET} PRIVATE
    QT_NO_CAST_TO_ASCII
    QT_NO_CAST_FROM_ASCII
)

if(NOT MSVC)
    target_compile_options(${SIGNON_QT_TARGET} PRIVATE -fvisibility=hidden)
endif()

# ---- Install ----
include(GNUInstallDirs)
include(CMakePackageConfigHelpers)

install(TARGETS ${SIGNON_QT_TARGET}
    EXPORT SignOnQt6Targets
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

# libsignon-qt.pri: headers.path = $$INSTALL_PREFIX/include/$$TARGET/SignOn
# (extension headers live in the per-class subdirectories)
install(FILES ${SIGNON_PUBLIC_HEADERS}
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/signon-qt6/SignOn)

# libsignon-qt.pri: headers.files lists the extension-less forwarding headers
# (AuthService / AuthSession / Error / Identity / IdentityInfo / SecurityContext /
# SessionData; each just #include <SignOn/xxx.h>) next to the public headers, at
# include/<TARGET>/SignOn — consumers use #include <SignOn/Identity>.
install(FILES
        ${SIGNON_SRC_DIR}/AuthService
        ${SIGNON_SRC_DIR}/AuthSession
        ${SIGNON_SRC_DIR}/Error
        ${SIGNON_SRC_DIR}/Identity
        ${SIGNON_SRC_DIR}/IdentityInfo
        ${SIGNON_SRC_DIR}/SecurityContext
        ${SIGNON_SRC_DIR}/SessionData
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/signon-qt6/SignOn
)

# CMake package: SignOnQt6 (consumers use the SIGNONQT_* variables upstream's
# SignOnQt5Config.cmake.in provides, and the imported target)
install(EXPORT SignOnQt6Targets
    NAMESPACE SignOnQt6::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/SignOnQt6
    FILE SignOnQt6Targets.cmake)

configure_package_config_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/SignOnQt6Config.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/SignOnQt6Config.cmake
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/SignOnQt6
)

write_basic_package_version_file(
    ${CMAKE_CURRENT_BINARY_DIR}/SignOnQt6ConfigVersion.cmake
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)

install(FILES
    ${CMAKE_CURRENT_BINARY_DIR}/SignOnQt6Config.cmake
    ${CMAKE_CURRENT_BINARY_DIR}/SignOnQt6ConfigVersion.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/SignOnQt6
)

# pkg-config (upstream substitutes libsignon-qt5.pc.in via QMAKE_SUBSTITUTES)
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/libsignon-qt6.pc.in
    ${CMAKE_CURRENT_BINARY_DIR}/libsignon-qt6.pc @ONLY)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/libsignon-qt6.pc
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/pkgconfig)

# ---- Upstream test suite (tests/libsignon-qt-tests/libsignon-qt-tests.pro) ----
# Optional: the suite drives the library against a running signond daemon over
# the session bus, so it is off by default and never part of the package.
option(SIGNON_QT_BUILD_TESTS "Build the upstream libsignon-qt test suite" OFF)
if(SIGNON_QT_BUILD_TESTS)
    find_package(Qt6 REQUIRED COMPONENTS Test)

    add_executable(libsignon-qt-tests
        ${CMAKE_CURRENT_SOURCE_DIR}/tests/libsignon-qt-tests/testauthsession.cpp
        ${CMAKE_CURRENT_SOURCE_DIR}/tests/libsignon-qt-tests/testthread.cpp
        ${CMAKE_CURRENT_SOURCE_DIR}/tests/libsignon-qt-tests/signon-ui.cpp
        ${CMAKE_CURRENT_SOURCE_DIR}/tests/libsignon-qt-tests/ssotestclient.cpp
        ${CMAKE_CURRENT_SOURCE_DIR}/tests/libsignon-qt-tests/testauthserviceresult.cpp
        ${CMAKE_CURRENT_SOURCE_DIR}/tests/libsignon-qt-tests/testidentityresult.cpp
    )
    target_include_directories(libsignon-qt-tests PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/tests/libsignon-qt-tests
        ${CMAKE_CURRENT_SOURCE_DIR}/lib
        ${CMAKE_CURRENT_SOURCE_DIR}/lib/plugins
        ${CMAKE_CURRENT_SOURCE_DIR}/src/plugins/test
    )
    target_compile_definitions(libsignon-qt-tests PRIVATE
        SSO_CI_TESTMANAGEMENT
        "SIGNOND_PLUGINS_DIR=\"${CMAKE_CURRENT_BINARY_DIR}/src/plugins/test\""
    )
    target_link_libraries(libsignon-qt-tests PRIVATE ${SIGNON_QT_TARGET} Qt6::Core Qt6::DBus Qt6::Test)
endif()
