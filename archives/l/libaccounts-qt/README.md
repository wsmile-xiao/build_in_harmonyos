# libaccounts-qt

## What is it?

libaccounts-qt is a Qt5 library that provides an API for managing online account configurations and authentication tokens. It works with the accounts framework (libaccounts-glib) to store and retrieve account information.

## Key Features

- Qt5-based API for account management
- Integration with the accounts framework (libaccounts-glib)
- Supports multiple account types and services

## OHOS/HarmonyOS Adaptation

- **Build type**: qmake (upstream) → CMake (custom)
- **Dependencies**: qt5-qtbase/5.15.2.2, libaccounts-glib/1.27, glib2/2.88.0
- **3 patches required**:
  - Accounts/account.h — fix deprecated QString::null
  - Accounts/manager.h — fix deprecated QString::
  - accounts-qt.pro — remove tests from SUBDIRS
- **Custom CMakeLists.txt**: Replaces qmake since the qt5-qtbase conan package does not ship qmake

## Version 1.13

- Status: published
- Build date: 2026-08-27
- Conan recipe: conanfile.py + conandata.yml + test_package/
- 3 patches applied
