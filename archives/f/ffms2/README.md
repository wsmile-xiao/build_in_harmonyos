# ffms2

FFmpegSource (FFMS2) is a cross-platform wrapper library around FFmpeg that provides frame- and sample-accurate access to media files.

## Features

- Easy to use API for opening and decompressing media files
- Frame-accurate video access
- Sample-accurate audio access
- Supports most common audio and video formats

## Dependencies

- FFmpeg (libavformat, libavcodec, libswscale, libavutil, libswresample)
- zlib

## Installation

Precompiled packages are available from cmd-pkgs repository.

## Usage

The main tool is `ffmsindex`, which creates index files for media files to enable frame-accurate seeking.

