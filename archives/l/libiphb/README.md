# libiphb

Library for interacting with the MeeGo/Sailfish OS heartbeat daemon.

## Description

libiphb is a library for managing heartbeat functionality on MeeGo/Sailfish OS devices. It provides an interface to interact with the device's power management and heartbeat daemon.

## Dependencies

- glib-2.0
- dbus-1

## Adaptation Notes

This library has been adapted for OpenHarmony by removing dependencies on:
- mce (Mode Control Entity) - Sailfish OS specific
- libdsme (Device State Management Entity) - Sailfish OS specific

The library provides core heartbeat functionality for applications that need to interact with system power management.