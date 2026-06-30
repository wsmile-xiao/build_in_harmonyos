# watchexec

Executes commands in response to file modifications — a file watcher and command runner.

## Description

watchexec is a modern, cross-platform file watcher and command runner. It monitors
files for changes and automatically reruns commands when modifications are detected.
It supports various filtering options, signal handling, and clear event modes.

## Key Features
- Watches files and directories for changes
- Executes commands in response to file modifications
- Supports glob patterns, path-based filtering, and event types
- Signal forwarding and process grouping
- Interactive mode with keyboard controls
- Notification support (--notify)

## Version Information
- **2.3.2-r0**: Precompiled dynamic musl binary, requires stub libdbus-1.so.3

## Platform Notes (HarmonyOS/musl)
- Static musl binaries from GitHub crash on HarmonyOS kernel (SIGSEGV)
- Dynamic musl binary works with system ld-musl-aarch64.so.1
- dbus stub library required (--notify feature uses libdbus-1.so.3)
- libgcc_s.so.1 required for Rust runtime

## Homebrew Popularity
4784 downloads
