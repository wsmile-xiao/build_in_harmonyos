# bubblewrap

Sandbox/unprivileged container tool using Linux user namespaces.

## Description

bubblewrap (bwrap) is a sandboxing tool that uses Linux user namespaces to create
isolated environments for running applications. It is commonly used by Flatpak and
other containerization systems.

## Key Features

- Unprivileged sandbox creation using user namespaces
- Network namespace isolation
- PID namespace isolation
- Bind mount support for sharing host resources
- Overlay filesystem support

## Dependencies

- libcap 2.69

## Available Versions

- 0.11.0 (built, 2026-05-26)
