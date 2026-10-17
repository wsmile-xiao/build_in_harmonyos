# gifify

gifify is a Node.js CLI tool that converts any video file to an optimized animated GIF.

It uses ffmpeg, convert (ImageMagick), and gifsicle as external tools to process the video.

## Features
- Convert any video file to an optimized GIF
- Options for colors, compression, FPS, resize, subtitles, speed
- Supports piping from stdin

## Runtime Dependencies
- ffmpeg (with libass and fontconfig support)
- convert (ImageMagick, with fontconfig support)
- gifsicle (with lossy support)
- Node.js runtime

## Version 2.4.0
- Status: built (2026-08-06)
- Build system: custom (npm project, npm install --omit=dev)
- Conan recipe: conanfile.py + conandata.yml + test_package/
- No ELF binaries (pure Node.js)

## Source
https://github.com/vvo/gifify
