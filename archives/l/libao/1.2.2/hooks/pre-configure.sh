#!/bin/bash
# Pre-configure hook for libao 1.2.2
# Purpose: Generate configure script using autoreconf
# Required for autotools-based build system

set -e

echo "[HOOK] Running autoreconf to generate configure script..."
autoreconf -isf

echo "[HOOK] Configure script generated successfully"