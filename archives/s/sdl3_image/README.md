# SDL3_image (SDL_image 3.x)

SDL_image is an image loading library that works with SDL3. It supports loading various image formats including BMP, GIF, JPEG, PNG, TIFF, WebP, and many more.

## Version

- **3.4.4** (built) - Static library for OpenHarmony aarch64

## Dependencies

- SDL3 (>= 3.4.0)

## Build Notes

- Uses cmake build system
- Requires CMAKE_SYSTEM_NAME=Linux on OpenHarmony (platform not recognized by SDL cmake)
- Built as static library only (SDL3 shared library fails on OpenHarmony due to missing pthread_setcanceltype)
- Disabled heavy dependencies (AVIF, JXL, WebP, TIFF, PNG) for minimal build