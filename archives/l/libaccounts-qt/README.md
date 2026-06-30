# libaccounts-qt

## What is it?

libaccounts-qt is a Qt library that provides an API for managing online account configurations and authentication tokens. It works with the accounts framework to store and retrieve account information.

## Key Features

- Qt-based API for account management
- Integration with the accounts framework
- Supports multiple account types and services

## OHOS/HarmonyOS Adaptation

- **Build type**: qmake
- **3 patches required**:
  - Accounts/account.h — header compatibility
  - Accounts/manager.h — header compatibility
  - accounts-qt.pro — build system adaptation

## Version 1.13

- Status: published
- Build date: 2026-06-09
- 3 patches applied