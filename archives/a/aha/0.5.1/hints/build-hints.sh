#!/bin/bash
# Build hints for aha 0.5.1
# This is a manual Makefile project (no configure script)

# Skip configure step
configure() {
    echo "No configure step for aha (manual Makefile project)"
    return 0
}

# Build command
build() {
    make PREFIX=$DEFAULT_PREFIX -j1
}

# Install command
install() {
    # Manual install because 'install' command is not available on OHOS
    mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
    mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/share/man/man1
    cp aha $TEST_PREFIX/$DEFAULT_PREFIX/bin/
    chmod 755 $TEST_PREFIX/$DEFAULT_PREFIX/bin/aha
    cp aha.1 $TEST_PREFIX/$DEFAULT_PREFIX/share/man/man1/
    chmod 644 $TEST_PREFIX/$DEFAULT_PREFIX/share/man/man1/aha.1
}
