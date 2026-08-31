cmake_minimum_required(VERSION 3.15)
project(accounts-qt5 CXX)

# ---- AUTOMOC for Q_OBJECT headers ----
set(CMAKE_AUTOMOC ON)

# ---- Find Qt5 via Conan-generated CMakeDeps ----
find_package(Qt5 COMPONENTS Core Xml REQUIRED)

# ---- Find libaccounts-glib via Conan-generated CMakeDeps ----
find_package(libaccounts-glib REQUIRED)
find_package(glib2 REQUIRED)

# ---- Source files ----
set(PUBLIC_HEADERS
    Accounts/accountscommon.h
    Accounts/Manager
    Accounts/manager.h
    Accounts/Account
    Accounts/account.h
    Accounts/AccountService
    Accounts/account-service.h
    Accounts/Application
    Accounts/application.h
    Accounts/AuthData
    Accounts/auth-data.h
    Accounts/Error
    Accounts/error.h
    Accounts/Provider
    Accounts/provider.h
    Accounts/Service
    Accounts/service.h
    Accounts/ServiceType
    Accounts/service-type.h
)

set(PRIVATE_HEADERS
    Accounts/manager_p.h
    Accounts/utils.h
)

set(SOURCES
    Accounts/manager.cpp
    Accounts/account.cpp
    Accounts/account-service.cpp
    Accounts/application.cpp
    Accounts/auth-data.cpp
    Accounts/error.cpp
    Accounts/provider.cpp
    Accounts/service.cpp
    Accounts/service-type.cpp
    Accounts/utils.cpp
)

# ---- Library target ----
add_library(accounts-qt5 ${SOURCES} ${PUBLIC_HEADERS} ${PRIVATE_HEADERS})

target_include_directories(accounts-qt5
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}
        ${CMAKE_CURRENT_SOURCE_DIR}/Accounts
)

target_link_libraries(accounts-qt5
    PUBLIC
        Qt5::Core
        Qt5::Xml
        libaccounts-glib::libaccounts-glib
        glib2::glib2
)

# glib2's gio-unix-2.0 headers (gdesktopappinfo.h etc.) live in a separate
# include directory not exposed via CMakeDeps; add it from conanfile variable.
if(DEFINED GLIB_GIO_UNIX_INCLUDE_DIR)
    target_include_directories(accounts-qt5 PRIVATE ${GLIB_GIO_UNIX_INCLUDE_DIR})
endif()

target_compile_features(accounts-qt5 PUBLIC cxx_std_11)

# Match upstream compile flags
target_compile_definitions(accounts-qt5 PRIVATE
    BUILDING_ACCOUNTS_QT
    QT_NO_CAST_TO_ASCII
    QT_NO_CAST_FROM_ASCII
    QT_NO_KEYWORDS
)

if(NOT MSVC)
    target_compile_options(accounts-qt5 PRIVATE
        -fno-exceptions
        -fvisibility=hidden
    )
endif()

# ---- Install ----
include(GNUInstallDirs)

install(TARGETS accounts-qt5
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

# Install headers to include/accounts-qt/
install(DIRECTORY Accounts/
    DESTINATION include/accounts-qt/Accounts
    FILES_MATCHING
        PATTERN "*.h"
        PATTERN "*.pri" EXCLUDE
        PATTERN "*.pc.in" EXCLUDE
        PATTERN "*.cmake.in" EXCLUDE
)

# Also install the bare header-name files (Manager, Account, etc.)
install(FILES
    Accounts/Manager
    Accounts/Account
    Accounts/AccountService
    Accounts/Application
    Accounts/AuthData
    Accounts/Error
    Accounts/Provider
    Accounts/Service
    Accounts/ServiceType
    DESTINATION include/accounts-qt/Accounts
)
