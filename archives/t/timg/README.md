# timg — Terminal Image Viewer

timg is a terminal image and video viewer. It uses various output protocols
supported by the terminal to display images, including Sixel, iTerm2, Kitty,
half/quarter blocks, and unicode blocks.

## Features

- Displays images in terminal using various protocols
- Supports JPEG, PNG, GIF, BMP, PSD, TGA and many other formats (via STB or GraphicsMagick)
- SVG support (via librsvg)
- PDF rendering (via poppler)
- Video playback (via ffmpeg)
- Sixel output for compatible terminals
- iTerm2 and Kitty graphics protocol support

## Current Build Configuration

The current build (1.6.3) uses a minimal feature set:
- STB image loading (built-in, no external deps)
- QOI image loading (built-in)
- Libsixel output (requires libsixel)
- libdeflate (optional compression)
- Video decoding, GraphicsMagick, TurboJPEG, RSVG, and Poppler are disabled
  (missing pre-compiled dependencies on OHOS platform)

## Homepage

https://github.com/hzeller/timg