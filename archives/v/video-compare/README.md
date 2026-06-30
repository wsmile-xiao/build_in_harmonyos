# video-compare — Video Comparison Tool

video-compare is a visual comparison tool for video files. It allows side-by-side
comparison of two video files with synchronized playback, making it easy to identify
differences in encoding, transcoding, or processing.

## Features

- Side-by-side video playback with synchronized controls
- Supports multiple video formats via FFmpeg
- Split-screen and overlay comparison modes
- Keyboard-driven interface for efficient navigation
- Frame-by-frame comparison with time offset adjustment

## Current Build Configuration

The current build (20260502) uses:
- FFmpeg 8.1.1 (pre-compiled package) for video decoding
- SDL2 2.30.0 (pre-compiled package) for display output
- SDL2_ttf 2.24.0 (compiled from source, cmake build) for text rendering
- Simple Makefile build with CXX=clang++ and USE_PKG_CONFIG=1
- No source modifications, all via make parameter overrides

## Homepage

https://github.com/pixop/video-compare