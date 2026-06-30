# arduino-cli

Arduino Command Line Interface (CLI) — the official command-line tool for Arduino.

## Overview

arduino-cli is a Go-based command line tool that provides all the features of the Arduino IDE from the command line. It supports board management, library management, sketch compilation and upload, and more.

## Key Features

- Board/core management (install, update, list)
- Library management (install, update, list, search)
- Sketch compilation and upload
- Configuration management
- gRPC server mode for IDE integration

## Build Requirements

- Go 1.21+ (CGO_ENABLED=0 for static compilation)
- GOPROXY=https://goproxy.cn,direct

## Version History

| Version | Status | Notes |
|---------|--------|-------|
| 1.5.0 | initialized | Latest stable release |