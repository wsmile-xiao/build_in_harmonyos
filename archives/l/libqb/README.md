# libqb

Library providing high performance client server reusable components.

## Overview

libqb is a library that provides high-performance client-server reusable components such as logging, tracing, inter-process communication (IPC), and polling.

## Features

- High-performance logging with multiple backends
- Inter-process communication (IPC) mechanisms
- Event polling abstraction
- Tracing capabilities
- Memory pooling

## Dependencies

- glib >= 2.0
- systemd (optional, for systemd journal logging)

## Building

```bash
./configure --prefix=/storage/Users/currentUser/usr/local --disable-man --disable-examples
make -j$(nproc)
make install DESTDIR=/path/to/staging
```

## Categories

- library
- ipc
- logging

## Links

- Homepage: https://github.com/ClusterLabs/libqb
- Documentation: https://libqb.readthedocs.io/